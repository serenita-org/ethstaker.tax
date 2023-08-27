import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from "unplugin-vue-components/vite";
import {BootstrapVueNextResolver} from "unplugin-vue-components/resolvers";

// https://vitejs.dev/config/
export default defineConfig({
  base: "/preview",
  plugins: [
      vue(),
      Components({
          resolvers: [BootstrapVueNextResolver()],
      }),
  ],
})
