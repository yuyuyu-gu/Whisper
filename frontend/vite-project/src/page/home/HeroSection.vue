<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const carouselItems = [
  {
    src: '/archives/reading-room.jpg',
    title: '校史档案阅览室',
    desc: '珍藏学校发展历程中的重要文献与影像资料。',
  },
  {
    src: '/archives/exhibition-hall.jpg',
    title: '校史陈列展厅',
    desc: '以时间为轴，讲述校园的百年变迁与辉煌时刻。',
  },
  {
    src: '/archives/digital-archive.jpg',
    title: '数字化档案平台',
    desc: '借助智能语音技术，实现多媒体档案的智能检索与展示。',
  },
]

const carouselIndex = ref(0)
let carouselTimer = null

function nextSlide() {
  carouselIndex.value = (carouselIndex.value + 1) % carouselItems.length
}

function prevSlide() {
  carouselIndex.value = (carouselIndex.value - 1 + carouselItems.length) % carouselItems.length
}

function startCarousel() {
  stopCarousel()
  carouselTimer = setInterval(() => {
    nextSlide()
  }, 6000)
}

function stopCarousel() {
  if (carouselTimer) {
    clearInterval(carouselTimer)
    carouselTimer = null
  }
}

onMounted(() => {
  startCarousel()
})

onBeforeUnmount(() => {
  stopCarousel()
})
</script>

<template>
  <section class="hero">
    <div class="hero-carousel" @mouseenter="stopCarousel" @mouseleave="startCarousel">
      <div class="carousel-window">
        <div
          v-for="(item, idx) in carouselItems"
          :key="item.title"
          class="carousel-slide"
          :class="{ active: idx === carouselIndex }"
        >
          <div class="carousel-image" :style="{ backgroundImage: `url(${item.src})` }"></div>
          <div class="carousel-caption">
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
          </div>
        </div>
      </div>
      <button type="button" class="carousel-nav prev" @click="prevSlide">‹</button>
      <button type="button" class="carousel-nav next" @click="nextSlide">›</button>
      <div class="carousel-dots">
        <button
          v-for="(item, idx) in carouselItems"
          :key="item.title + idx"
          type="button"
          :class="['dot', { active: idx === carouselIndex }]"
          @click="carouselIndex = idx"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero {
  display: grid;
  grid-template-columns: minmax(0, 12fr) minmax(0, 1.5fr);
  gap: 1.5rem;
  margin-bottom: 1.5rem;
  align-items: center;
}

.hero-text {
  padding: 1rem 0.75rem 1rem 0;
}

.hero-tag {
  display: inline-block;
  padding: 0.1rem 0.75rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.8);
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.hero h2 {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #111827;
}

.hero-desc {
  margin-top: 0.6rem;
  font-size: 0.9rem;
  line-height: 1.7;
  color: #4b5563;
}

.hero-carousel {
  position: relative;
  border-radius: 0.75rem;
  overflow: hidden;
  background: radial-gradient(circle at top left, #fef3c7, #e5e7eb 40%, #f9fafb 70%);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.18);
}

.carousel-window {
  position: relative;
  height: 700px;
}

.carousel-slide {
  position: absolute;
  inset: 0;
  opacity: 0;
  transform: translateX(8px) scale(1.02);
  transition: opacity 600ms ease, transform 600ms ease;
  display: flex;
  flex-direction: column;
}

.carousel-slide.active {
  opacity: 1;
  transform: translateX(0) scale(1);
}

.carousel-image {
  flex: 1;
  background-size: cover;
  background-position: center;
  filter: saturate(0.9) contrast(1.02);
}

.carousel-caption {
  padding: 0.6rem 0.9rem 0.7rem;
  background: linear-gradient(to right, rgba(17, 24, 39, 0.92), rgba(30, 64, 175, 0.85));
  color: #f9fafb;
}

.carousel-caption h3 {
  margin: 0 0 0.2rem;
  font-size: 0.95rem;
  font-weight: 600;
}

.carousel-caption p {
  margin: 0;
  font-size: 0.8rem;
  opacity: 0.95;
}

.carousel-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  border: none;
  background: rgba(17, 24, 39, 0.55);
  color: #f9fafb;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
}

.carousel-nav.prev {
  left: 0.4rem;
}

.carousel-nav.next {
  right: 0.4rem;
}

.carousel-nav:hover {
  background: rgba(15, 23, 42, 0.85);
}

.carousel-dots {
  position: absolute;
  bottom: 0.4rem;
  right: 0.7rem;
  display: flex;
  gap: 0.3rem;
}

.dot {
  width: 0.35rem;
  height: 0.35rem;
  border-radius: 999px;
  border: none;
  background: rgba(249, 250, 251, 0.7);
  cursor: pointer;
}

.dot.active {
  width: 0.8rem;
  background: #fbbf24;
}

@media (max-width: 640px) {
  .hero {
    grid-template-columns: minmax(0, 1fr);
  }
  .carousel-window {
    height: 210px;
  }
}
</style>
