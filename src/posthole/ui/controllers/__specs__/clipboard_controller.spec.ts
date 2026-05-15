import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ClipboardController from "../clipboard_controller.ts";
import { mountController } from "../../__specs__/helpers.ts";

const FIXTURE = `
  <div data-controller="clipboard" data-clipboard-text-value="copied-text">
    <button data-action="click->clipboard#copy" data-clipboard-target="button">
      <span data-clipboard-target="defaultIcon">copy</span>
      <span data-clipboard-target="successIcon" class="hidden">check</span>
    </button>
  </div>
`;

type Clipboard = InstanceType<typeof ClipboardController>;

let teardown: (() => void) | undefined;
let originalClipboard: typeof navigator.clipboard | undefined;

function installClipboard(writeText: (text: string) => Promise<void>): void {
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  originalClipboard = navigator.clipboard;
});

afterEach(() => {
  teardown?.();
  teardown = undefined;
  vi.useRealTimers();
  if (originalClipboard) {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: originalClipboard,
    });
  } else {
    // @ts-expect-error — restore the missing-property state for envs without clipboard
    delete navigator.clipboard;
  }
});

describe("clipboard_controller", () => {
  it("copy() writes the text value to navigator.clipboard and flashes the success icon", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    installClipboard(writeText);

    const { controller, root, unmount } = await mountController<Clipboard>({
      identifier: "clipboard",
      controllerClass: ClipboardController,
      html: FIXTURE,
    });
    teardown = unmount;

    await controller.copy();

    expect(writeText).toHaveBeenCalledWith("copied-text");
    const defaultIcon = root.querySelector<HTMLElement>('[data-clipboard-target="defaultIcon"]')!;
    const successIcon = root.querySelector<HTMLElement>('[data-clipboard-target="successIcon"]')!;
    expect(defaultIcon.classList.contains("hidden")).toBe(true);
    expect(successIcon.classList.contains("hidden")).toBe(false);
  });

  it("reverts the icon after the flash timer elapses", async () => {
    installClipboard(vi.fn().mockResolvedValue(undefined));

    const { controller, root, unmount } = await mountController<Clipboard>({
      identifier: "clipboard",
      controllerClass: ClipboardController,
      html: FIXTURE,
    });
    teardown = unmount;

    await controller.copy();
    vi.advanceTimersByTime(1500);

    const defaultIcon = root.querySelector<HTMLElement>('[data-clipboard-target="defaultIcon"]')!;
    const successIcon = root.querySelector<HTMLElement>('[data-clipboard-target="successIcon"]')!;
    expect(defaultIcon.classList.contains("hidden")).toBe(false);
    expect(successIcon.classList.contains("hidden")).toBe(true);
  });

  it("does not swap icons when writeText rejects", async () => {
    installClipboard(vi.fn().mockRejectedValue(new Error("blocked")));

    const { controller, root, unmount } = await mountController<Clipboard>({
      identifier: "clipboard",
      controllerClass: ClipboardController,
      html: FIXTURE,
    });
    teardown = unmount;

    await controller.copy();

    const successIcon = root.querySelector<HTMLElement>('[data-clipboard-target="successIcon"]')!;
    expect(successIcon.classList.contains("hidden")).toBe(true);
  });

  it("is a no-op when navigator.clipboard is unavailable", async () => {
    // @ts-expect-error — simulate clipboard-less environment (insecure context / old browser)
    delete navigator.clipboard;

    const { controller, root, unmount } = await mountController<Clipboard>({
      identifier: "clipboard",
      controllerClass: ClipboardController,
      html: FIXTURE,
    });
    teardown = unmount;

    await expect(controller.copy()).resolves.toBeUndefined();
    const successIcon = root.querySelector<HTMLElement>('[data-clipboard-target="successIcon"]')!;
    expect(successIcon.classList.contains("hidden")).toBe(true);
  });
});
