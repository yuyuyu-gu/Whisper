import { createRouter, createWebHistory } from "vue-router";
import Login from "../page/login.vue";
import Home from "../page/home.vue";

const routes = [
  { path: "/", redirect: "/login" },
  { path: "/login", component: Login },
  { path: "/home", component: Home },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
