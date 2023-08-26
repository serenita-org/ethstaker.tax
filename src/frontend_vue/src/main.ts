import { createApp } from 'vue'
import './style.scss'
import App from './App.vue'
import Chart from "chart.js/auto";

const app = createApp(App);

Chart.defaults.font.family = "Raleway Sans";

app.mount("#app");
