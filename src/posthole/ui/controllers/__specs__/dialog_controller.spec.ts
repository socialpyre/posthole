import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DialogController from "../dialog_controller.ts";
import { mountController } from "../../__specs__/helpers.ts";

type Dialog = InstanceType<typeof DialogController>;

const TRIGGER_FIXTURE = `
  <button data-controller="dialog"
          data-dialog-id-value="my-dialog"
          data-action="click->dialog#open">Open</button>
  <dialog id="my-dialog">
    <button data-dialog-skip-focus aria-label="Close">x</button>
    <input id="first-field" name="username" />
    <input id="second-field" name="display_name" />
    <button type="submit">Save</button>
  </dialog>
`;

const PRE_OPEN_FIXTURE = `
  <dialog id="pre-open" data-controller="dialog" open>
    <button data-dialog-skip-focus aria-label="Close">x</button>
    <input id="invalid-field" name="username" aria-invalid="true" />
    <input id="other-field" name="display_name" />
    <button type="submit">Save</button>
  </dialog>
`;

const CLOSE_FIXTURE = `
  <dialog id="closable" data-controller="dialog" open>
    <button id="close-btn" data-action="click->dialog#close">Cancel</button>
  </dialog>
`;

let teardown: (() => void) | undefined;
let showModalMock: ReturnType<typeof vi.fn>;
let closeMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  // jsdom doesn't implement ``HTMLDialogElement.showModal`` / ``close`` at
  // all — define them here so the controller's modal-promotion path runs.
  // We flip the ``open`` attribute manually so attribute-based assertions
  // in the controller (and the tests) reflect the toggle.
  showModalMock = vi.fn(function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  });
  closeMock = vi.fn(function (this: HTMLDialogElement) {
    this.removeAttribute("open");
  });
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: showModalMock,
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true,
    value: closeMock,
  });
});

afterEach(() => {
  teardown?.();
  teardown = undefined;
  // @ts-expect-error — remove patched props so each test starts clean
  delete HTMLDialogElement.prototype.showModal;
  // @ts-expect-error — remove patched props so each test starts clean
  delete HTMLDialogElement.prototype.close;
});

describe("dialog_controller", () => {
  it("trigger.open() calls showModal on the target dialog and focuses the first non-skipped field", async () => {
    const { controller, unmount } = await mountController<Dialog>({
      identifier: "dialog",
      controllerClass: DialogController,
      html: TRIGGER_FIXTURE,
    });
    teardown = unmount;

    controller.open();

    const dialog = document.getElementById("my-dialog") as HTMLDialogElement;
    expect(showModalMock).toHaveBeenCalledTimes(1);
    expect(dialog.hasAttribute("open")).toBe(true);
    expect(document.activeElement?.id).toBe("first-field");
  });

  it("pre-rendered open dialog promotes to a real modal on connect", async () => {
    const { unmount } = await mountController<Dialog>({
      identifier: "dialog",
      controllerClass: DialogController,
      html: PRE_OPEN_FIXTURE,
    });
    teardown = unmount;

    expect(showModalMock).toHaveBeenCalledTimes(1);
    // Focus lands on the aria-invalid field, not the close button or the
    // first DOM-order field, so users see their error context.
    expect(document.activeElement?.id).toBe("invalid-field");
  });

  it("close action closes the closest dialog", async () => {
    const { unmount } = await mountController<Dialog>({
      identifier: "dialog",
      controllerClass: DialogController,
      html: CLOSE_FIXTURE,
    });
    teardown = unmount;

    const dialog = document.getElementById("closable") as HTMLDialogElement;
    const button = document.getElementById("close-btn") as HTMLButtonElement;
    button.click();

    expect(closeMock).toHaveBeenCalled();
    expect(dialog.hasAttribute("open")).toBe(false);
  });

  it("open() is a no-op when no target id resolves", async () => {
    const { controller, unmount } = await mountController<Dialog>({
      identifier: "dialog",
      controllerClass: DialogController,
      html: `<button data-controller="dialog" data-dialog-id-value="missing"></button>`,
    });
    teardown = unmount;

    expect(() => controller.open()).not.toThrow();
    expect(showModalMock).not.toHaveBeenCalled();
  });
});
