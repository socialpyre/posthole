import "@hotwired/turbo";
import { Application } from "@hotwired/stimulus";
import HelloController from "./controllers/hello_controller.ts";

const app = Application.start();
app.register("hello", HelloController);

declare global {
  interface Window {
    Stimulus: Application;
  }
}

window.Stimulus = app;
