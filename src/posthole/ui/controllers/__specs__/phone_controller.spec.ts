import { afterEach, beforeEach, describe, expect, it } from "vitest";

import PhoneController from "../phone_controller.ts";
import { mountController } from "../../__specs__/helpers.ts";

const FIXTURE = `
  <div data-controller="phone">
    <button data-phone-target="chip"
            data-action="click->phone#select"
            data-preset="iphone-14-pro" data-active aria-pressed="true">iPhone 14 Pro</button>
    <button data-phone-target="chip"
            data-action="click->phone#select"
            data-preset="iphone-14" aria-pressed="false">iPhone 14</button>
    <button data-phone-target="chip"
            data-action="click->phone#select"
            data-preset="google-pixel-6-pro" aria-pressed="false">Pixel 6 Pro</button>

    <div data-phone-target="device" class="device device-iphone-14-pro"></div>
  </div>
`;

const syntheticClick = (target: HTMLElement): Event =>
  ({ currentTarget: target }) as unknown as Event;

function chip(root: HTMLElement, preset: string): HTMLButtonElement {
  const el = root.querySelector<HTMLButtonElement>(`button[data-preset="${preset}"]`);
  if (!el) throw new Error(`fixture missing chip ${preset}`);
  return el;
}

function device(root: HTMLElement): HTMLElement {
  const el = root.querySelector<HTMLElement>('[data-phone-target="device"]');
  if (!el) throw new Error("fixture missing device target");
  return el;
}

let teardown: (() => void) | undefined;

beforeEach(() => {
  try {
    localStorage.removeItem("posthole:phone-preset");
  } catch {
    // ignore
  }
  document.documentElement.removeAttribute("data-phone-preset");
});

afterEach(() => {
  teardown?.();
  teardown = undefined;
});

describe("phone_controller", () => {
  it("renders the server-default preset on mount", async () => {
    const { root, unmount } = await mountController({
      identifier: "phone",
      controllerClass: PhoneController,
      html: FIXTURE,
    });
    teardown = unmount;

    expect(device(root).classList.contains("device-iphone-14-pro")).toBe(true);
    expect(chip(root, "iphone-14-pro").getAttribute("aria-pressed")).toBe("true");
  });

  it("select() swaps the device-* class and chip pressed state", async () => {
    const { root, controller, unmount } = await mountController<PhoneController>({
      identifier: "phone",
      controllerClass: PhoneController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.select(syntheticClick(chip(root, "google-pixel-6-pro")));

    const d = device(root);
    expect(d.classList.contains("device-iphone-14-pro")).toBe(false);
    expect(d.classList.contains("device-google-pixel-6-pro")).toBe(true);
    expect(chip(root, "google-pixel-6-pro").getAttribute("aria-pressed")).toBe("true");
    expect(chip(root, "iphone-14-pro").getAttribute("aria-pressed")).toBe("false");
  });

  it("persists selection to localStorage and stamps <html data-phone-preset>", async () => {
    const { root, controller, unmount } = await mountController<PhoneController>({
      identifier: "phone",
      controllerClass: PhoneController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.select(syntheticClick(chip(root, "iphone-14")));

    expect(localStorage.getItem("posthole:phone-preset")).toBe("iphone-14");
    expect(document.documentElement.getAttribute("data-phone-preset")).toBe("iphone-14");
  });

  it("reads persisted preset on connect", async () => {
    localStorage.setItem("posthole:phone-preset", "google-pixel-6-pro");

    const { root, unmount } = await mountController({
      identifier: "phone",
      controllerClass: PhoneController,
      html: FIXTURE,
    });
    teardown = unmount;

    expect(device(root).classList.contains("device-google-pixel-6-pro")).toBe(true);
    expect(device(root).classList.contains("device-iphone-14-pro")).toBe(false);
  });

  it("ignores unknown presets", async () => {
    const { root, controller, unmount } = await mountController<PhoneController>({
      identifier: "phone",
      controllerClass: PhoneController,
      html: FIXTURE,
    });
    teardown = unmount;

    const fake = document.createElement("button");
    fake.dataset.preset = "fictional-phone-99";
    controller.select(syntheticClick(fake));

    expect(device(root).classList.contains("device-iphone-14-pro")).toBe(true);
    expect(localStorage.getItem("posthole:phone-preset")).toBe(null);
  });
});
