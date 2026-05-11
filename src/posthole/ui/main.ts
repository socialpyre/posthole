import "@hotwired/turbo";
import { Application } from "@hotwired/stimulus";

import HelloController from "./controllers/hello_controller.ts";
import SidebarController from "./controllers/sidebar_controller.ts";
import ThemeController from "./controllers/theme_controller.ts";

declare global {
  interface Window {
    Stimulus: Application;
  }
}

const app = Application.start();

app.register("hello", HelloController);
app.register("sidebar", SidebarController);
app.register("theme", ThemeController);

window.Stimulus = app;
