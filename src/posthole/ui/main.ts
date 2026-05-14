import "@hotwired/turbo";
import { Application } from "@hotwired/stimulus";

import CarouselController from "./controllers/carousel_controller.ts";
import HelloController from "./controllers/hello_controller.ts";
import ListSelectionController from "./controllers/list_selection_controller.ts";
import PhoneController from "./controllers/phone_controller.ts";
import SearchController from "./controllers/search_controller.ts";
import SidebarController from "./controllers/sidebar_controller.ts";
import TabsController from "./controllers/tabs_controller.ts";
import ThemeController from "./controllers/theme_controller.ts";

declare global {
  interface Window {
    Stimulus: Application;
  }
}

const app = Application.start();

app.register("carousel", CarouselController);
app.register("hello", HelloController);
app.register("list-selection", ListSelectionController);
app.register("phone", PhoneController);
app.register("search", SearchController);
app.register("sidebar", SidebarController);
app.register("tabs", TabsController);
app.register("theme", ThemeController);

window.Stimulus = app;

// Turbo Frame swaps don't touch <head>, so document.title stays stale on
// frame-scoped navigation. Each frame response carries its title in a
// `<span data-frame-title>` child; copy that onto document.title here.
// Drive visits (back/forward/refresh) re-render <head> and bypass this path.
document.addEventListener("turbo:frame-render", (event) => {
  const frame = event.target as HTMLElement;
  const title = frame.querySelector<HTMLElement>("[data-frame-title]")?.textContent?.trim();
  if (title) document.title = title;
});
