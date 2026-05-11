import { Application } from "@hotwired/stimulus";

// Stimulus's ControllerConstructor type isn't reliably re-exported across versions;
// pull the constructor type structurally from Application#register's signature.
type ControllerClass = Parameters<Application["register"]>[1];

interface MountOptions {
  identifier: string;
  controllerClass: ControllerClass;
  html: string;
}

interface Mounted<C> {
  app: Application;
  root: HTMLElement;
  controller: C;
  unmount: () => void;
}

export async function mountController<C>(options: MountOptions): Promise<Mounted<C>> {
  document.body.innerHTML = options.html;
  const app = Application.start();
  app.register(options.identifier, options.controllerClass);

  // Stimulus connects via MutationObserver, which fires on a microtask.
  await Promise.resolve();
  await Promise.resolve();

  const selector = `[data-controller~="${options.identifier}"]`;
  const root = document.querySelector<HTMLElement>(selector);
  if (!root) {
    const message = `fixture missing ${selector}`;
    throw new Error(message);
  }

  const controller = app.getControllerForElementAndIdentifier(root, options.identifier) as C | null;
  if (!controller) {
    const message = `controller "${options.identifier}" did not connect`;
    throw new Error(message);
  }

  return {
    app,
    root,
    controller,
    unmount: () => {
      app.stop();
      document.body.innerHTML = "";
    },
  };
}
