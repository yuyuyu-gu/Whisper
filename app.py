import os
import sys
import asyncio
import time
from typing import List, Optional, Tuple
from uuid import uuid4
import gradio as gr
from gradio_i18n import Translate, gettext as _

from core.config import AppConfig, parse_app_config
from core.context import create_app_context
from modules.utils.paths import DEFAULT_PARAMETERS_CONFIG_PATH, I18N_YAML_PATH
from modules.utils.files_manager import load_yaml, MEDIA_EXTENSION
from modules.ui.htmls import *
from modules.utils.youtube_manager import get_ytmetas
from modules.whisper.data_classes import *
from modules.utils.logger import get_logger
from services.auth.service import AuthService
from services.jobs.manager import BackgroundJobManager
logger = get_logger()

# 修复 Windows 上 asyncio 的连接重置警告
def handle_exception(loop, context):
    """处理 asyncio 异常，避免 Windows 连接重置错误显示"""
    exception = context.get('exception')
    if isinstance(exception, ConnectionResetError):
        # Windows 上的连接重置错误通常是正常的，可以忽略
        if exception.errno == 10054:  # WinError 10054
            # 这是一个常见的 Windows 网络问题，不影响应用运行
            pass
        else:
            # 其他连接重置错误仍然记录
            logger.debug(f"Asyncio connection error: {exception}")
    elif isinstance(exception, OSError):
        # 其他 OSError 也可能正常，不记录
        if hasattr(exception, 'winerror') and exception.winerror == 10054:
            pass
        else:
            logger.debug(f"Asyncio OSError: {exception}")
    else:
        # 其他异常正常处理
        logger.warning(f"Asyncio exception: {context}")

# 在 Windows 上设置 asyncio 异常处理器
if sys.platform == 'win32':
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果循环已在运行，设置异常处理器
            loop.set_exception_handler(handle_exception)
        else:
            # 如果循环未运行，在下次创建时设置
            def create_loop():
                loop = asyncio.new_event_loop()
                loop.set_exception_handler(handle_exception)
                return loop
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        # 如果设置失败，不影响应用运行
        pass

class App:
    def __init__(self, config: AppConfig):
        self.config = config
        self.app = gr.Blocks(css=CSS, theme=self.config.theme, delete_cache=(3600, 86400))
        self.context = create_app_context(self.config, logger)
        self.whisper_inf = self.context.whisper
        self.nllb_inf = self.context.nllb
        self.deepl_api = self.context.deepl_api
        self.text_corrector = self.context.text_corrector
        self.temp_chat_service = self.context.rag_chat_service
        self.auth_service = AuthService(
            db_path=self.config.auth_db_path,
            default_admin_username=self.config.default_admin_username,
            default_admin_password=self.config.default_admin_password,
            logger=logger,
        )
        self.auth_service.init_db()
        self.job_manager = BackgroundJobManager(
            max_workers=self.config.max_background_workers,
            logger=logger,
        )
        self.auth_db_path = self.config.auth_db_path
        self.default_admin_username = self.config.default_admin_username
        self.default_admin_password = self.config.default_admin_password
        self.i18n = load_yaml(I18N_YAML_PATH)
        self.default_params = load_yaml(DEFAULT_PARAMETERS_CONFIG_PATH)
        try:
            if isinstance(self.default_params, dict):
                whisper_defaults = self.default_params.setdefault("whisper", {})
                whisper_defaults.pop("initial_prompt", None)
        except Exception:
            pass

        logger.info(
            f"Use \"{self.config.whisper_type}\" implementation\n"
            f"Device \"{self.whisper_inf.device}\" is detected"
        )

    def register_user(self, username: Optional[str], password: Optional[str]):
        return self.auth_service.register_user(username, password)

    def login_user(self, username: Optional[str], password: Optional[str]):
        return self.auth_service.login_user(username, password)

    def get_pending_users(self):
        return self.auth_service.get_pending_users()

    def approve_user(self, username: Optional[str]):
        return self.auth_service.approve_user(username)

    def get_all_users(self):
        """获取所有用户列表（不包括当前主账号admin）"""
        return self.auth_service.get_all_users()

    def grant_admin_role(self, target_username: Optional[str], current_username: Optional[str]):
        """赋予用户管理员权限（仅主账号admin可操作）"""
        return self.auth_service.grant_admin_role(target_username, current_username)

    def revoke_admin_role(self, target_username: Optional[str], current_username: Optional[str]):
        """撤销用户管理员权限（仅主账号admin可操作）"""
        return self.auth_service.revoke_admin_role(target_username, current_username)

    def create_pipeline_inputs(self):
        whisper_params = self.default_params["whisper"]
        vad_params = self.default_params["vad"]
        diarization_params = self.default_params["diarization"]
        uvr_params = self.default_params["bgm_separation"]

        with gr.Row():
            dd_model = gr.Dropdown(choices=self.whisper_inf.available_models, value=whisper_params["model_size"],
                                   label=_("Model"), allow_custom_value=True)
            dd_lang = gr.Dropdown(choices=self.whisper_inf.available_langs + [AUTOMATIC_DETECTION],
                                  value=AUTOMATIC_DETECTION if whisper_params["lang"] == AUTOMATIC_DETECTION.unwrap()
                                  else whisper_params["lang"], label=_("Language"))
            dd_file_format = gr.Dropdown(choices=["SRT", "WebVTT", "txt", "LRC"], value=whisper_params["file_format"], label=_("File Format"))
        # with gr.Row():
        #     cb_translate = gr.Checkbox(value=whisper_params["is_translate"], label=_("Translate to English?"),
        #                                interactive=True)
        # 创建一个占位符，因为 cb_translate 已被注释掉
        cb_translate = gr.Checkbox(value=False, label=_("Translate to English?"), visible=False)
        
        with gr.Row():
            cb_timestamp = gr.Checkbox(value=whisper_params["add_timestamp"],
                                       label=_("Add a timestamp to the end of the filename"),
                                       interactive=True)

        with gr.Accordion(_("Advanced Parameters"), open=False):
            whisper_inputs = WhisperParams.to_gradio_inputs(defaults=whisper_params, only_advanced=True,
                                                            whisper_type=self.config.whisper_type,
                                                            available_compute_types=self.whisper_inf.available_compute_types,
                                                            compute_type=self.whisper_inf.current_compute_type)
            # Keep initial prompt slot in pipeline inputs to satisfy parameter mapping, but hide from UI
            tb_initial_prompt_state = gr.State(GRADIO_NONE_STR)
            whisper_inputs.insert(8, tb_initial_prompt_state)

        with gr.Accordion(_("Background Music Remover Filter"), open=False):
            uvr_inputs = BGMSeparationParams.to_gradio_input(defaults=uvr_params,
                                                             available_models=self.whisper_inf.music_separator.available_models,
                                                             available_devices=self.whisper_inf.music_separator.available_devices,
                                                             device=self.whisper_inf.music_separator.device)

        with gr.Accordion(_("Voice Detection Filter"), open=False):
            vad_inputs = VadParams.to_gradio_inputs(defaults=vad_params)

        with gr.Accordion(_("Diarization"), open=False):
            diarization_inputs = DiarizationParams.to_gradio_inputs(defaults=diarization_params,
                                                                    available_devices=self.whisper_inf.diarizer.available_device,
                                                                    device=self.whisper_inf.diarizer.device)

        pipeline_inputs = [dd_model, dd_lang, cb_translate] + whisper_inputs + vad_inputs + diarization_inputs + uvr_inputs

        return (
            pipeline_inputs,
            dd_file_format,
            cb_timestamp
        )

    def launch(self):
        with self.app:
            lang = gr.Radio(
                choices=list(self.i18n.keys()),
                label="Language",
                interactive=True,
                visible=False,
            )
            with Translate(self.i18n):
                def _empty_user_state():
                    return {"username": None, "role": None, "authenticated": False}

                auth_state = gr.State(_empty_user_state())

                with gr.Column(elem_id="login_view_container") as login_view:
                    gr.Markdown("### 登录 Whisper WebUI")
                    gr.Markdown("如无账号，可直接输入新用户名和密码注册，注册后需管理员审批。")
                    tb_login_username = gr.Textbox(label="用户名", placeholder="请输入用户名")
                    tb_login_password = gr.Textbox(label="密码", placeholder="请输入密码", type="password")
                    with gr.Row():
                        btn_login = gr.Button("登录", variant="primary")
                        btn_register = gr.Button("注册", variant="secondary")
                    login_feedback = gr.Markdown("")

                with gr.Column(visible=False) as main_view:
#-------------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(MARKDOWN, elem_id="md_project")
                            gr.HTML(POSTMESSAGE_FIX_JS)
                    with gr.Row():
                        user_info_box = gr.Markdown("", elem_id="current_user_info")
                        btn_logout = gr.Button("退出登录", variant="secondary")
                    with gr.Accordion("管理员审核面板", open=False, visible=False) as admin_panel:
                        gr.Markdown("仅管理员可见，用于批准新注册用户。")
                        pending_users_dropdown = gr.Dropdown(
                            label="待审核用户",
                            choices=[],
                            value=None,
                            multiselect=False,
                            interactive=True
                        )
                        with gr.Row():
                            btn_refresh_pending = gr.Button("刷新待审核列表", size="sm")
                            btn_approve_pending = gr.Button("批准选中用户", variant="primary", size="sm")
                        admin_feedback = gr.Markdown("")
                        
                        # 管理员权限管理（仅主账号admin可见）
                        with gr.Accordion("管理员权限管理", open=False, visible=False) as admin_role_panel:
                            gr.Markdown("**仅主账号 admin 可见**，用于赋予或撤销其他用户的管理员权限。")
                            all_users_dropdown = gr.Dropdown(
                                label="选择用户",
                                choices=[],
                                value=None,
                                multiselect=False,
                                interactive=True
                            )
                            user_role_display = gr.Markdown("")
                            with gr.Row():
                                btn_refresh_users = gr.Button("刷新用户列表", size="sm")
                                btn_grant_admin = gr.Button("赋予管理员权限", variant="primary", size="sm")
                                btn_revoke_admin = gr.Button("撤销管理员权限", variant="stop", size="sm")
                        admin_role_feedback = gr.Markdown("")
                    with gr.Accordion("RAG 知识库管理", open=False, visible=False) as rag_panel:
                        gr.Markdown("仅管理员可见，用于重新索引本地知识库，使 RAG 纠错能够读取最新 Markdown/Text 文档。")
                        btn_update_kb = gr.Button("更新知识库索引", variant="primary")
                        rag_update_feedback = gr.Markdown("")
                    with gr.Accordion("后台任务监控", open=False, visible=False) as jobs_panel:
                        gr.Markdown("仅管理员可见，用于查看最近的后台任务执行情况。")
                        btn_refresh_jobs = gr.Button("刷新任务状态", size="sm")
                        jobs_status_md = gr.Markdown("", elem_id="jobs_status")
                    with gr.Tabs():
                        with gr.TabItem(_("File")):  # tab1
                            gr.Markdown("#### 一键转写字幕")
                            gr.Markdown(
                                "支持上传媒体文件或指定本地文件夹。按需配置 Whisper/VAD/分轨等参数，点击开始即可生成字幕并自动执行 RAG 纠错。"
                            )
                            with gr.Row(equal_height=False):
                                with gr.Column(scale=5, min_width=420, elem_id="file_tab_controls"):
                                    with gr.Group():
                                        gr.Markdown("**1. 选择输入源**")
                                        input_file = gr.Files(type="filepath", label=_("Upload File here"), file_types=MEDIA_EXTENSION)
                                        tb_input_folder = gr.Textbox(
                                            label="Input Folder Path (Optional)",
                                            info="可选：使用本地目录中的音频/视频文件，留空则使用上方上传的文件。",
                                            visible=self.config.colab,
                                            value="",
                                        )
                                        cb_include_subdirectory = gr.Checkbox(
                                            label="Include Subdirectory Files",
                                            info="勾选后会扫描子目录中的全部文件。",
                                            visible=self.config.colab,
                                            value=False,
                                        )
                                        cb_save_same_dir = gr.Checkbox(
                                            label="Save outputs at same directory",
                                            info="当使用本地目录时，是否将输出文件同步写回原目录。",
                                            visible=self.config.colab,
                                            value=True,
                                        )

                                    with gr.Accordion(_("转录参数设置（可选）"), open=False):
                                        pipeline_params, dd_file_format, cb_timestamp = self.create_pipeline_inputs()

                                    with gr.Group():
                                        gr.Markdown("**2. 运行任务**")
                                        with gr.Row():
                                            btn_run = gr.Button(_("GENERATE SUBTITLE FILE"), variant="primary")
                                            job_status_md = gr.Markdown("", elem_id="transcription_job_status")
                                        with gr.Accordion(_("后处理选项（可选）"), open=False):
                                            cb_convert_t2s = gr.Checkbox(
                                                label="Convert Traditional to Simplified (T->S)",
                                                value=True,
                                                info="启用后会在导出前做繁转简。",
                                            )

                                with gr.Column(scale=5, min_width=420, elem_id="file_tab_results"):
                                    with gr.Group():
                                        gr.Markdown("**输出与纠错**")
                                        tb_corrected_output = gr.Textbox(
                                            label="RAG 纠错文本",
                                            lines=10,
                                            interactive=False,
                                            placeholder="运行后展示 Qwen RAG 纠错后的文本",
                                        )
                                        files_subtitles = gr.Files(label=_("Downloadable output file"), interactive=False)
                                        btn_openfolder = gr.Button('📂 打开输出目录', scale=1)

                                    with gr.Group():
                                        gr.Markdown("**字幕关键词查找**")
                                        with gr.Row():
                                            tb_keyword = gr.Textbox(label="关键词", placeholder="输入要查找的词语", lines=1)
                                            dd_sub_file = gr.Dropdown(label="选择字幕文件", choices=[], allow_custom_value=True)
                                        btn_search_keyword = gr.Button("在字幕中查找", variant="secondary")
                                        tb_search_result = gr.Textbox(
                                            label="查找结果",
                                            lines=8,
                                            interactive=False,
                                            placeholder="点击“在字幕中查找”后显示包含该词的句子",
                                        )

                            # 纠错功能关闭，仅输出 Whisper 原始文本
                            state_whisper_hidden = gr.State("")
                            state_sub_paths = gr.State([])

                            params = [
                                input_file,
                                tb_input_folder,
                                cb_include_subdirectory,
                                cb_save_same_dir,
                                dd_file_format,
                                cb_timestamp,
                                cb_convert_t2s,
                            ]
                            params = params + pipeline_params

                            def _submit_transcription_job(*job_params):
                                result, job_id = self.job_manager.run_sync(
                                    "transcription",
                                    self.whisper_inf.transcribe_file,
                                    *job_params,
                                )
                                status = f"任务 {job_id} 已完成 ✅" if job_id else "任务已完成"
                                if isinstance(result, tuple):
                                    result = list(result)
                                elif not isinstance(result, list):
                                    result = [result]
                                # 预期 result: [whisper_text, subtitle_text, files]
                                if len(result) < 3:
                                    result = (result + ["", [], None])[:3]
                                whisper_text = result[0]
                                subtitle_text = result[1]
                                files_out = result[2] or []
                                file_choices = files_out if isinstance(files_out, list) else []
                                dd_update = gr.update(choices=file_choices, value=file_choices[0] if file_choices else None)
                                return whisper_text, subtitle_text, files_out, status, dd_update, file_choices

                            btn_run.click(
                                fn=_submit_transcription_job,
                                inputs=params,
                                outputs=[state_whisper_hidden, tb_corrected_output, files_subtitles, job_status_md, dd_sub_file, state_sub_paths],
                            )
                            btn_openfolder.click(fn=lambda: self.open_folder("outputs"), inputs=None, outputs=None)
#-------------------------------------------------------------------------------------------------------------
                        # 字幕关键词查找功能
                        def _search_keyword(keyword: str, file_path: str, stored_paths: list):
                            keyword = (keyword or "").strip()
                            if not keyword:
                                return "请先输入关键词。"
                            candidate = file_path or ""
                            if not candidate and stored_paths:
                                candidate = stored_paths[0]
                            if not candidate:
                                return "请先选择或生成字幕文件。"
                            try:
                                if not os.path.exists(candidate):
                                    return f"文件不存在：{candidate}"
                                lines = []
                                with open(candidate, "r", encoding="utf-8", errors="ignore") as f:
                                    for line in f:
                                        stripped = line.strip()
                                        if not stripped:
                                            continue
                                        if "-->" in stripped:
                                            continue
                                        if stripped.isdigit():
                                            continue
                                        lines.append(stripped)
                                if not lines:
                                    return "未能读取字幕内容。"
                                kw = keyword.lower()
                                matched = [ln for ln in lines if kw in ln.lower()]
                                if not matched:
                                    return f"未在文件中找到关键词：{keyword}"
                                preview = "\n".join(matched[:30])
                                if len(matched) > 30:
                                    preview += f"\n... 共 {len(matched)} 处匹配，已截断显示前 30 条。"
                                return preview
                            except Exception as exc:
                                logger.error(f"字幕关键词查找失败: {exc}", exc_info=True)
                                return f"查找失败：{exc}"

                        btn_search_keyword.click(
                            fn=_search_keyword,
                            inputs=[tb_keyword, dd_sub_file, state_sub_paths],
                            outputs=[tb_search_result],
                        )
#-------------------------------------------------------------------------------------------------------------
                        # 访谈助手（RAG）功能已移除

                        # Translation and BGM tabs removed per request

                        with gr.TabItem("图像搜索"):
                            # Initialize face search service once
                            if not hasattr(self, "face_search"):
                                self.face_search = self.context.face_search_service

                            gr.Markdown("#### 以图搜图 · 人脸检索")
                            gr.Markdown("上传一张包含人脸的图片，系统将基于人脸特征在数据库中查找最相似的结果，可对结果执行批量重命名和数据库维护。")

                            with gr.Row(equal_height=False):
                                with gr.Column(scale=4, min_width=360, elem_id="face_search_controls"):
                                    with gr.Group():
                                        gr.Markdown("**1. 上传查询图像**")
                                        img_query = gr.Image(
                                            type="filepath",
                                            label="上传人脸图像",
                                            height=240,
                                            show_download_button=False,
                                        )
                                        with gr.Row():
                                            btn_detect_faces = gr.Button("检测人脸", variant="secondary", size="sm")
                                        img_face_detection = gr.Image(
                                            type="filepath",
                                            label="人脸检测结果",
                                            height=300,
                                            show_download_button=True,
                                            visible=False,
                                        )
                                        tb_face_info = gr.Textbox(
                                            label="检测信息",
                                            interactive=False,
                                            lines=3,
                                            visible=False,
                                        )
                                        tb_result_prefix = gr.Textbox(
                                            label="结果重命名前缀（仅管理员可见）",
                                            placeholder="例如：张三_",
                                            lines=1,
                                            visible=False,
                                        )
                                    with gr.Group():
                                        gr.Markdown("**2. 设置搜索参数**")
                                        num_top_k = gr.Slider(
                                            minimum=1,
                                            maximum=100,
                                            value=50,
                                            step=1,
                                            label="返回结果数量 (top_k)",
                                        )
                                        max_dist = gr.Slider(
                                            minimum=0.1,
                                            maximum=1.0,
                                            value=0.75,
                                            step=0.05,
                                            label="最大距离阈值（越小越相似）",
                                        )
                                        with gr.Row():
                                            btn_search = gr.Button("搜索相似图像", variant="primary")
                                            btn_rename_results = gr.Button("批量加前缀", variant="secondary", visible=False)
                                        tb_status = gr.Textbox(label="状态", interactive=False, lines=3)
                                        state_ranked_results = gr.State([])

                                    with gr.Group():
                                        gr.Markdown("**数据库统计**")
                                        btn_refresh_stats = gr.Button("刷新统计", size="sm")
                                        tb_stats = gr.Textbox(
                                            label="统计信息",
                                            interactive=False,
                                            lines=4,
                                            value="点击“刷新统计”查看当前数据库规模。",
                                        )

                                    with gr.Accordion("数据库运维", open=False):
                                        with gr.Tabs():
                                            with gr.Tab("添加图像"):
                                                files_to_add = gr.Files(
                                                    type="filepath",
                                                    label="上传图像添加到数据库（支持多选）",
                                                )
                                                btn_add = gr.Button("添加到数据库")
                                                gr.Markdown("或批量导入整个文件夹：")
                                                fe_folder = gr.File(
                                                    label="选择文件夹",
                                                    file_count="directory",
                                                    type="filepath",
                                                )
                                                cb_folder_include_sub = gr.Checkbox(
                                                    label="包含子目录",
                                                    value=True,
                                                )
                                                btn_add_folder = gr.Button("批量导入文件夹")
                                            with gr.Tab("删除 / 清理"):
                                                files_to_delete = gr.Files(
                                                    type="filepath",
                                                    label="选择要删除的图像",
                                                )
                                                btn_delete = gr.Button("从数据库删除", variant="stop")
                                                with gr.Row():
                                                    btn_cleanup = gr.Button("清理孤儿记录", size="sm")
                                                    btn_clear_db = gr.Button("清空数据库", variant="stop", size="sm")

                                with gr.Column(scale=8, min_width=520, elem_id="face_search_results"):
                                    with gr.Group():
                                        gr.Markdown("**搜索结果预览**")
                                        gallery = gr.Gallery(
                                            label="搜索结果",
                                            columns=5,
                                            height=520,
                                            show_label=True,
                                        )

                        def _safe_rename_file(original_path: str, prefix: str):
                            base_dir = os.path.dirname(original_path)
                            basename = os.path.basename(original_path)
                            if basename.startswith(prefix):
                                return original_path, "skip"
                            name, ext = os.path.splitext(basename)
                            candidate = f"{prefix}{basename}"
                            new_path = os.path.join(base_dir, candidate)
                            counter = 1
                            while os.path.exists(new_path):
                                candidate = f"{prefix}{name}_{counter}{ext}"
                                new_path = os.path.join(base_dir, candidate)
                                counter += 1
                                if counter > 1000:
                                    return original_path, "重命名失败：达到重试上限。"
                            try:
                                os.rename(original_path, new_path)
                                updated_count, errors = self.face_search.rename_indexed_image(original_path, new_path)
                                if errors:
                                    return original_path, errors[0]
                                if updated_count == 0:
                                    logger.warning(f"未找到与 {original_path} 匹配的数据库记录，已重命名文件。")
                                return new_path, None
                            except Exception as exc:
                                logger.error(f"重命名文件失败: {original_path} -> {new_path}", exc_info=True)
                                return original_path, str(exc)

                        def _apply_prefix_to_ranked(ranked_pairs, prefix):
                            cleaned_prefix = prefix.strip()
                            if not cleaned_prefix:
                                return ranked_pairs, ""
                            renamed = 0
                            skipped = 0
                            errors = []
                            updated_pairs = []
                            for path, distance in ranked_pairs:
                                new_path, error = _safe_rename_file(path, cleaned_prefix)
                                if error:
                                    if error == "skip":
                                        skipped += 1
                                    else:
                                        errors.append(f"{os.path.basename(path)}: {error}")
                                    updated_pairs.append((path, distance))
                                else:
                                    if new_path != path:
                                        renamed += 1
                                    else:
                                        skipped += 1
                                    updated_pairs.append((new_path, distance))
                            summary_parts = []
                            if renamed:
                                summary_parts.append(f"已为 {renamed} 张图片添加前缀“{cleaned_prefix}”。")
                            if skipped:
                                summary_parts.append(f"{skipped} 张图片已包含该前缀或无需修改。")
                            if errors:
                                preview = "; ".join(errors[:3])
                                if len(errors) > 3:
                                    preview += f"... 等 {len(errors)} 项"
                                summary_parts.append(f"部分图片重命名失败：{preview}")
                            return updated_pairs, "\n".join(summary_parts).strip()

                        def _detect_faces(query_path: str):
                            """检测图像中的人脸并可视化"""
                            try:
                                if not query_path:
                                    return gr.update(value=None, visible=False), gr.update(value="请先上传图像。", visible=False)
                                
                                vis_path, face_count, face_info_list = self.face_search.detect_and_visualize_faces(query_path)
                                
                                if vis_path is None:
                                    return gr.update(value=None, visible=False), gr.update(value="检测失败：无法处理图像。", visible=True)
                                
                                if face_count == 0:
                                    return gr.update(value=None, visible=False), gr.update(value="未检测到人脸。", visible=True)
                                
                                # 构建信息文本
                                info_lines = [f"检测到 {face_count} 张人脸："]
                                for info in face_info_list:
                                    idx = info.get("index", 0)
                                    bbox = info.get("bbox", [])
                                    conf = info.get("confidence")
                                    age = info.get("age")
                                    gender = info.get("gender")
                                    
                                    info_parts = [f"人脸 {idx}: 位置({bbox[0]}, {bbox[1]}) - ({bbox[2]}, {bbox[3]})"]
                                    if conf is not None:
                                        info_parts.append(f"置信度: {conf:.2f}")
                                    if age is not None:
                                        info_parts.append(f"年龄: {age}")
                                    if gender is not None:
                                        info_parts.append(f"性别: {gender}")
                                    info_lines.append(" | ".join(info_parts))
                                
                                info_text = "\n".join(info_lines)
                                return gr.update(value=vis_path, visible=True), gr.update(value=info_text, visible=True)
                                
                            except ValueError as e:
                                return gr.update(value=None, visible=False), gr.update(value=f"检测失败: {str(e)}", visible=True)
                            except Exception as e:
                                logger.error(f"人脸检测出错: {e}", exc_info=True)
                                return gr.update(value=None, visible=False), gr.update(value=f"检测失败: {str(e)}", visible=True)

                        def _face_search(query_path: str, top_k: int, max_distance: float):
                            try:
                                if not query_path:
                                    return [], "请先上传查询图像。", []
                                
                                ranked = self.face_search.search_by_image_with_scores(
                                    query_path,
                                    top_k=int(top_k),
                                    max_distance=float(max_distance)
                                )
                                
                                if not ranked:
                                    return [], "未找到相似图像。请尝试调整搜索参数或添加更多图像到数据库。", []
                                
                                gallery_items = [
                                    (p, "")
                                    for p, _ in ranked
                                ]
                                status_msg = f"找到 {len(gallery_items)} 张相似图像。"
                                return gallery_items, status_msg, ranked
                            except ValueError as e:
                                return [], f"搜索失败: {str(e)}", []
                            except Exception as e:
                                logger.error(f"搜索出错: {e}", exc_info=True)
                                return [], f"搜索失败: {str(e)}", []

                        def _rename_ranked_results(prefix_text: str, ranked_pairs: Optional[List[Tuple[str, float]]], user_state: dict):
                            # 检查权限：只有管理员才能重命名
                            if not user_state or not user_state.get("authenticated"):
                                return [], "请先登录后再执行该操作。", ranked_pairs or []
                            if user_state.get("role") != "admin":
                                return [], "只有管理员账号才能对图片进行重命名前缀。", ranked_pairs or []
                            
                            cleaned_prefix = (prefix_text or "").strip()
                            stored_pairs = ranked_pairs or []
                            if not cleaned_prefix:
                                return [], "请输入重命名前缀后再执行该操作。", stored_pairs
                            if not stored_pairs:
                                return [], "请先执行搜索，并确保存在可重命名的结果。", stored_pairs

                            updated_pairs, summary = _apply_prefix_to_ranked(stored_pairs, cleaned_prefix)
                            gallery_items = [
                                (p, "")
                                for p, _ in updated_pairs
                            ]
                            status_msg = summary or f"为 {len(updated_pairs)} 个结果完成检查，未检测到需要重命名的文件。"
                            return gallery_items, status_msg, updated_pairs

                        def _face_add(files: list):
                            try:
                                if not files:
                                    return "请上传要添加的图像。"
                                
                                paths = [f.name if isinstance(f, gr.utils.NamedString) else f for f in files]
                                processed, faces, errors = self.face_search.add_images(paths)
                                
                                msg = f"成功索引 {processed} 张图像，添加 {faces} 个人脸。"
                                if errors:
                                    error_count = len(errors)
                                    msg += f"\n警告: {error_count} 个文件处理失败。"
                                    if error_count <= 5:
                                        msg += "\n失败详情:\n" + "\n".join(errors[:5])
                                    else:
                                        msg += f"\n前5个失败详情:\n" + "\n".join(errors[:5])
                                        msg += f"\n... 还有 {error_count - 5} 个错误"
                                
                                return msg
                            except Exception as e:
                                logger.error(f"添加图像失败: {e}", exc_info=True)
                                return f"添加失败: {str(e)}"

                        def _face_add_folder(folder_obj, include_sub: bool):
                            try:
                                from modules.face_search.service import SUPPORTED_IMAGE_EXTENSIONS

                                if not folder_obj:
                                    return "请提供有效的文件夹路径。"

                                raw_items = folder_obj if isinstance(folder_obj, (list, tuple)) else [folder_obj]
                                candidate_paths = []
                                for item in raw_items:
                                    if isinstance(item, gr.utils.NamedString):
                                        candidate_paths.append(item.name)
                                    elif item:
                                        try:
                                            candidate_paths.append(os.fspath(item))
                                        except TypeError:
                                            continue
                                if not candidate_paths:
                                    return "请提供有效的文件夹路径。"

                                files_to_add = set()
                                visited_dirs = set()

                                def collect_from_directory(dir_path: str):
                                    if not dir_path or dir_path in visited_dirs:
                                        return
                                    visited_dirs.add(dir_path)
                                    if include_sub:
                                        for root, _, files in os.walk(dir_path):
                                            for fn in files:
                                                if os.path.splitext(fn)[1].lower() in SUPPORTED_IMAGE_EXTENSIONS:
                                                    files_to_add.add(os.path.join(root, fn))
                                    else:
                                        for fn in os.listdir(dir_path):
                                            fp = os.path.join(dir_path, fn)
                                            if os.path.isfile(fp) and os.path.splitext(fn)[1].lower() in SUPPORTED_IMAGE_EXTENSIONS:
                                                files_to_add.add(fp)

                                for path in candidate_paths:
                                    if not path:
                                        continue
                                    if os.path.isdir(path):
                                        collect_from_directory(path)
                                    elif os.path.isfile(path):
                                        if os.path.splitext(path)[1].lower() in SUPPORTED_IMAGE_EXTENSIONS:
                                            files_to_add.add(path)

                                if not files_to_add:
                                    return "文件夹中未找到支持的图像文件。"

                                processed, faces, errors = self.face_search.add_images(files_to_add)

                                msg = f"成功索引 {processed} 张图像，添加 {faces} 个人脸。"
                                if errors:
                                    error_count = len(errors)
                                    msg += f"\n警告: {error_count} 个文件处理失败。"
                                    if error_count <= 5:
                                        msg += "\n失败详情:\n" + "\n".join(errors[:5])
                                    else:
                                        msg += f"\n前5个失败详情:\n" + "\n".join(errors[:5])
                                        msg += f"\n... 还有 {error_count - 5} 个错误"

                                return msg
                            except Exception as e:
                                logger.error(f"添加文件夹失败: {e}", exc_info=True)
                                return f"添加文件夹失败: {str(e)}"
                        
                        def _face_delete(files: list):
                            try:
                                if not files:
                                    return "请选择要删除的图像。"
                                
                                paths = [f.name if isinstance(f, gr.utils.NamedString) else f for f in files]
                                deleted_count, errors = self.face_search.delete_images(paths)
                                
                                msg = f"成功删除 {deleted_count} 个人脸记录。"
                                if errors:
                                    msg += f"\n警告: {len(errors)} 个错误。\n" + "\n".join(errors[:3])
                                
                                return msg
                            except Exception as e:
                                logger.error(f"删除失败: {e}", exc_info=True)
                                return f"删除失败: {str(e)}"
                        
                        def _refresh_stats():
                            try:
                                stats = self.face_search.get_statistics()
                                msg = f"""数据库统计信息:
总人脸数: {stats['total_faces']}
唯一图像数: {stats['total_images']}
已索引文件数: {stats['total_indexed_files']}"""
                                return msg
                            except Exception as e:
                                logger.error(f"获取统计信息失败: {e}", exc_info=True)
                                return f"获取统计信息失败: {str(e)}"
                        
                        def _cleanup_orphaned():
                            try:
                                deleted_count, errors = self.face_search.remove_orphaned_entries()
                                msg = f"清理完成: 删除了 {deleted_count} 个孤儿记录。"
                                if errors:
                                    msg += f"\n警告: {len(errors)} 个错误。"
                                return msg
                            except Exception as e:
                                logger.error(f"清理失败: {e}", exc_info=True)
                                return f"清理失败: {str(e)}"
                        
                        def _clear_database():
                            try:
                                success = self.face_search.clear_database()
                                if success:
                                    return "数据库已清空。"
                                else:
                                    return "清空数据库失败，请查看日志。"
                            except Exception as e:
                                logger.error(f"清空数据库失败: {e}", exc_info=True)
                                return f"清空数据库失败: {str(e)}"

                        btn_detect_faces.click(
                            fn=_detect_faces,
                            inputs=[img_query],
                            outputs=[img_face_detection, tb_face_info]
                        )
                        btn_search.click(
                            fn=_face_search,
                            inputs=[img_query, num_top_k, max_dist],
                            outputs=[gallery, tb_status, state_ranked_results]
                        )
                        btn_rename_results.click(
                            fn=_rename_ranked_results,
                            inputs=[tb_result_prefix, state_ranked_results, auth_state],
                            outputs=[gallery, tb_status, state_ranked_results]
                        )
                        btn_add.click(fn=_face_add, inputs=[files_to_add], outputs=[tb_status])
                        btn_add_folder.click(
                            fn=_face_add_folder,
                            inputs=[fe_folder, cb_folder_include_sub],
                            outputs=[tb_status]
                        )
                        btn_delete.click(
                            fn=_face_delete,
                            inputs=[files_to_delete],
                            outputs=[tb_status]
                        )
                        btn_refresh_stats.click(
                            fn=_refresh_stats,
                            outputs=[tb_stats]
                        )
                        btn_cleanup.click(
                            fn=_cleanup_orphaned,
                            outputs=[tb_status]
                        )
                        btn_clear_db.click(
                            fn=_clear_database,
                            outputs=[tb_status]
                        )

            def _handle_register(username, password):
                success, message = self.register_user(username, password)
                prefix = "✅" if success else "⚠️"
                return f"{prefix} {message}"

            def _handle_login(username, password, current_state):
                success, role, message = self.login_user(username, password)
                dropdown_update = gr.update(value=None, choices=[])
                user_role_display = gr.update(value="")
                is_admin = False
                is_main_admin = False
                if success:
                    normalized_username = (username or "").strip()
                    new_state = {
                        "username": normalized_username,
                        "role": role,
                        "authenticated": True
                    }
                    is_admin = (role == "admin")
                    is_main_admin = (normalized_username == self.default_admin_username)
                    if is_admin:
                        pending = self.get_pending_users()
                        dropdown_update = gr.update(
                            choices=pending,
                            value=pending[0] if pending else None
                        )
                    role_label = "管理员" if role == "admin" else "普通用户"
                    user_role_display = gr.update(
                        value=f"当前登录账号：**{normalized_username}**（{role_label}）"
                    )
                    return (
                        new_state,
                        gr.update(visible=False),
                        gr.update(visible=True),
                        gr.update(visible=is_admin),
                        gr.update(visible=is_main_admin),
                        gr.update(visible=is_admin),
                        gr.update(visible=is_admin),
                        f"✅ {message}",
                        dropdown_update,
                        user_role_display,
                        gr.update(visible=is_admin),
                        gr.update(visible=is_admin)
                    )

                fallback_state = _empty_user_state()
                return (
                    fallback_state,
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    f"⚠️ {message}",
                    dropdown_update,
                    user_role_display,
                    gr.update(visible=False),
                    gr.update(visible=False)
                )

            def _handle_logout(current_state):
                message = "当前未登录。"
                if current_state and current_state.get("authenticated"):
                    message = f"用户 {current_state.get('username')} 已退出登录。"
                return (
                    _empty_user_state(),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    message,
                    gr.update(value=None, choices=[]),
                    gr.update(value=""),
                    gr.update(visible=False),
                    gr.update(visible=False)
                )

            def _refresh_pending(user_state):
                if not user_state or not user_state.get("authenticated"):
                    return gr.update(), "请先登录后再操作。"
                if user_state.get("role") != "admin":
                    return gr.update(), "仅管理员可以审核用户。"
                pending = self.get_pending_users()
                if pending:
                    return gr.update(choices=pending, value=pending[0]), f"共有 {len(pending)} 个待审核用户。"
                return gr.update(choices=[], value=None), "暂无待审核用户。"

            def _refresh_jobs_status(user_state):
                if not user_state or not user_state.get("authenticated"):
                    return "请先登录后再操作。"
                if user_state.get("role") != "admin":
                    return "仅管理员可以查看任务状态。"
                jobs = self.job_manager.list_jobs(limit=20)
                if not jobs:
                    return "暂无后台任务记录。"
                lines = []
                for job in jobs:
                    duration = ""
                    if job.get("finished_at") and (job.get("started_at") or job.get("submitted_at")):
                        start_ts = job.get("started_at") or job.get("submitted_at")
                        duration_value = max(0.0, job["finished_at"] - start_ts)
                        duration = f"，耗时 {duration_value:.1f}s"
                    error_msg = f"，错误：{job['error']}" if job.get("error") else ""
                    lines.append(f"- **{job['name']}** ({job['id']}): {job['status']}{duration}{error_msg}")
                return "\n".join(lines)

            def _approve_pending(selected_user, user_state):
                if not user_state or not user_state.get("authenticated"):
                    return gr.update(), "请先登录后再操作。"
                if user_state.get("role") != "admin":
                    return gr.update(), "仅管理员可以审核用户。"
                success, message = self.approve_user(selected_user)
                pending = self.get_pending_users()
                dropdown_update = gr.update(choices=pending, value=pending[0] if pending else None)
                prefix = "✅" if success else "⚠️"
                return dropdown_update, f"{prefix} {message}"

            def _refresh_users_list(user_state):
                if not user_state or not user_state.get("authenticated"):
                    return gr.update(), "", "请先登录后再操作。"
                if user_state.get("username") != self.default_admin_username:
                    return gr.update(), "", "仅主账号可以管理用户权限。"
                users = self.get_all_users()
                if not users:
                    return gr.update(choices=[], value=None), "", "暂无其他用户。"
                choices = [f"{u['username']} ({'管理员' if u['role'] == 'admin' else '普通用户'})" for u in users]
                selected_user = users[0] if users else None
                selected_display = f"{selected_user['username']} ({'管理员' if selected_user['role'] == 'admin' else '普通用户'})" if selected_user else None
                user_info = f"**当前用户列表：**\n" + "\n".join([f"- {u['username']}: {u['role']} ({u['status']})" for u in users])
                return gr.update(choices=choices, value=selected_display), user_info, ""

            def _on_user_selected(selected_value, user_state):
                if not selected_value or not user_state or not user_state.get("authenticated"):
                    return ""
                if user_state.get("username") != self.default_admin_username:
                    return ""
                # 从选择的值中提取用户名（格式：username (role)）
                username = selected_value.split(" (")[0] if " (" in selected_value else selected_value
                users = self.get_all_users()
                for u in users:
                    if u['username'] == username:
                        return f"**选中用户：** {u['username']}\n**当前角色：** {u['role']}\n**账号状态：** {u['status']}"
                return ""

            def _grant_admin(selected_user, user_state):
                if not user_state or not user_state.get("authenticated"):
                    return gr.update(), "", "请先登录后再操作。"
                if user_state.get("username") != self.default_admin_username:
                    return gr.update(), "", "仅主账号可以赋予管理员权限。"
                if not selected_user:
                    return gr.update(), "", "请选择要赋予管理员权限的用户。"
                # 从选择的值中提取用户名
                username = selected_user.split(" (")[0] if " (" in selected_user else selected_user
                success, message = self.grant_admin_role(username, user_state.get("username"))
                # 刷新用户列表
                users = self.get_all_users()
                choices = [f"{u['username']} ({'管理员' if u['role'] == 'admin' else '普通用户'})" for u in users]
                user_info = f"**当前用户列表：**\n" + "\n".join([f"- {u['username']}: {u['role']} ({u['status']})" for u in users])
                prefix = "✅" if success else "⚠️"
                return gr.update(choices=choices, value=selected_user if selected_user in choices else (choices[0] if choices else None)), user_info, f"{prefix} {message}"

            def _rebuild_rag_index(user_state):
                if not self.text_corrector:
                    return "⚠️ RAG 文本纠错未启用，无法更新知识库索引。"
                if not user_state or not user_state.get("authenticated"):
                    return "请先登录后再操作。"
                if user_state.get("role") != "admin":
                    return "仅管理员可以更新知识库索引。"
                kb_dir = self.config.rag_kb_dir
                try:
                    gr.Info("开始重建知识库索引，请稍候...")
                    message = self.text_corrector.rebuild_index(kb_dir)
                    logger.info("RAG 知识库索引已更新：%s", message)
                    return f"✅ {message}"
                except Exception as exc:
                    logger.error("更新 RAG 知识库索引失败：%s", exc, exc_info=True)
                    return f"⚠️ 更新失败：{exc}"

            def _revoke_admin(selected_user, user_state):
                if not user_state or not user_state.get("authenticated"):
                    return gr.update(), "", "请先登录后再操作。"
                if user_state.get("username") != self.default_admin_username:
                    return gr.update(), "", "仅主账号可以撤销管理员权限。"
                if not selected_user:
                    return gr.update(), "", "请选择要撤销管理员权限的用户。"
                # 从选择的值中提取用户名
                username = selected_user.split(" (")[0] if " (" in selected_user else selected_user
                success, message = self.revoke_admin_role(username, user_state.get("username"))
                # 刷新用户列表
                users = self.get_all_users()
                choices = [f"{u['username']} ({'管理员' if u['role'] == 'admin' else '普通用户'})" for u in users]
                user_info = f"**当前用户列表：**\n" + "\n".join([f"- {u['username']}: {u['role']} ({u['status']})" for u in users])
                prefix = "✅" if success else "⚠️"
                return gr.update(choices=choices, value=selected_user if selected_user in choices else (choices[0] if choices else None)), user_info, f"{prefix} {message}"

            btn_register.click(
                fn=_handle_register,
                inputs=[tb_login_username, tb_login_password],
                outputs=[login_feedback]
            )
            btn_login.click(
                fn=_handle_login,
                inputs=[tb_login_username, tb_login_password, auth_state],
                outputs=[auth_state, login_view, main_view, admin_panel, admin_role_panel, rag_panel, jobs_panel, login_feedback, pending_users_dropdown, user_info_box, tb_result_prefix, btn_rename_results]
            )
            btn_logout.click(
                fn=_handle_logout,
                inputs=[auth_state],
                outputs=[auth_state, login_view, main_view, admin_panel, admin_role_panel, rag_panel, jobs_panel, login_feedback, pending_users_dropdown, user_info_box, tb_result_prefix, btn_rename_results]
            )
            btn_refresh_pending.click(
                fn=_refresh_pending,
                inputs=[auth_state],
                outputs=[pending_users_dropdown, admin_feedback]
            )
            btn_approve_pending.click(
                fn=_approve_pending,
                inputs=[pending_users_dropdown, auth_state],
                outputs=[pending_users_dropdown, admin_feedback]
            )
            btn_refresh_users.click(
                fn=_refresh_users_list,
                inputs=[auth_state],
                outputs=[all_users_dropdown, user_role_display, admin_role_feedback]
            )
            all_users_dropdown.change(
                fn=_on_user_selected,
                inputs=[all_users_dropdown, auth_state],
                outputs=[user_role_display]
            )
            btn_grant_admin.click(
                fn=_grant_admin,
                inputs=[all_users_dropdown, auth_state],
                outputs=[all_users_dropdown, user_role_display, admin_role_feedback]
            )
            btn_revoke_admin.click(
                fn=_revoke_admin,
                inputs=[all_users_dropdown, auth_state],
                outputs=[all_users_dropdown, user_role_display, admin_role_feedback]
            )
            btn_update_kb.click(
                fn=_rebuild_rag_index,
                inputs=[auth_state],
                outputs=[rag_update_feedback]
            )
            btn_refresh_jobs.click(
                fn=_refresh_jobs_status,
                inputs=[auth_state],
                outputs=[jobs_status_md],
            )

        # Launch the app with optional gradio settings
        cfg = self.config
        self.app.queue(
            api_open=cfg.api_open
        ).launch(
            share=cfg.share,
            server_name=cfg.server_name,
            server_port=cfg.server_port,
            root_path=cfg.root_path if cfg.root_path else None,
            inbrowser=cfg.inbrowser,
            ssl_verify=cfg.ssl_verify,
            ssl_keyfile=cfg.ssl_keyfile,
            ssl_keyfile_password=cfg.ssl_keyfile_password,
            ssl_certfile=cfg.ssl_certfile,
            allowed_paths=eval(cfg.allowed_paths) if cfg.allowed_paths else None
        )

    @staticmethod
    def open_folder(folder_path: str):
        if os.path.exists(folder_path):
            os.system(f"start {folder_path}")
        else:
            os.makedirs(folder_path, exist_ok=True)
            logger.info(f"The directory path {folder_path} has newly created.")


def main():
    config = parse_app_config()
    application = App(config=config)
    application.launch()


if __name__ == "__main__":
    main()
