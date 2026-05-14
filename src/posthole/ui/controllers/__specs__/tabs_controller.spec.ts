import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TabsController from "../tabs_controller.ts";
import { mountController } from "../../__specs__/helpers.ts";

// Mirrors the data attrs the server emits: the controller has no
// hard-coded defaults; both the URL param name and the default panel key
// come from the template. Defaults to panel "a" so the "strip default"
// test can click tab-a without rewriting the fixture.
const FIXTURE = `
  <div data-controller="tabs"
       data-tabs-param-value="view"
       data-tabs-default-panel-value="a">
    <button id="tab-a" role="tab" aria-selected="true" tabindex="0"
            data-tabs-target="tab"
            data-action="click->tabs#select keydown->tabs#keydown"
            data-tabs-key="a">A</button>
    <button id="tab-b" role="tab" aria-selected="false" tabindex="-1"
            data-tabs-target="tab"
            data-action="click->tabs#select keydown->tabs#keydown"
            data-tabs-key="b">B</button>
    <button id="tab-c" role="tab" aria-selected="false" tabindex="-1"
            data-tabs-target="tab"
            data-action="click->tabs#select keydown->tabs#keydown"
            data-tabs-key="c">C</button>

    <div role="tabpanel" data-tabs-target="panel" data-panel="a">A</div>
    <div role="tabpanel" data-tabs-target="panel" data-panel="b" hidden>B</div>
    <div role="tabpanel" data-tabs-target="panel" data-panel="c" hidden>C</div>
  </div>
`;

function tab(root: HTMLElement, id: string): HTMLButtonElement {
  const el = root.querySelector<HTMLButtonElement>(`#${id}`);
  if (!el) throw new Error(`fixture missing #${id}`);
  return el;
}

function panel(root: HTMLElement, key: string): HTMLElement {
  const el = root.querySelector<HTMLElement>(`[data-panel="${key}"]`);
  if (!el) throw new Error(`fixture missing panel ${key}`);
  return el;
}

let teardown: (() => void) | undefined;

beforeEach(() => {
  // Reset URL before each test so persistence assertions are deterministic.
  history.replaceState(null, "", "/posts/abc");
});

afterEach(() => {
  teardown?.();
  teardown = undefined;
});

describe("tabs_controller", () => {
  it("initial state: first tab selected, others hidden", async () => {
    const { root, unmount } = await mountController({
      identifier: "tabs",
      controllerClass: TabsController,
      html: FIXTURE,
    });
    teardown = unmount;

    expect(tab(root, "tab-a").getAttribute("aria-selected")).toBe("true");
    expect(panel(root, "a").hidden).toBe(false);
    expect(panel(root, "b").hidden).toBe(true);
    expect(panel(root, "c").hidden).toBe(true);
  });

  it("click swaps aria-selected, tabindex, and hidden", async () => {
    const { root, unmount } = await mountController({
      identifier: "tabs",
      controllerClass: TabsController,
      html: FIXTURE,
    });
    teardown = unmount;

    tab(root, "tab-b").click();

    expect(tab(root, "tab-a").getAttribute("aria-selected")).toBe("false");
    expect(tab(root, "tab-b").getAttribute("aria-selected")).toBe("true");
    expect(tab(root, "tab-a").tabIndex).toBe(-1);
    expect(tab(root, "tab-b").tabIndex).toBe(0);
    expect(panel(root, "a").hidden).toBe(true);
    expect(panel(root, "b").hidden).toBe(false);
  });

  it("ArrowRight moves to the next tab", async () => {
    const { root, unmount } = await mountController({
      identifier: "tabs",
      controllerClass: TabsController,
      html: FIXTURE,
    });
    teardown = unmount;

    tab(root, "tab-a").dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }),
    );

    expect(tab(root, "tab-b").getAttribute("aria-selected")).toBe("true");
  });

  it("ArrowLeft wraps to the last tab from the first", async () => {
    const { root, unmount } = await mountController({
      identifier: "tabs",
      controllerClass: TabsController,
      html: FIXTURE,
    });
    teardown = unmount;

    tab(root, "tab-a").dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }),
    );

    expect(tab(root, "tab-c").getAttribute("aria-selected")).toBe("true");
  });

  it("selecting a non-default tab writes ?view= to the URL", async () => {
    const { root, unmount } = await mountController({
      identifier: "tabs",
      controllerClass: TabsController,
      html: FIXTURE,
    });
    teardown = unmount;

    tab(root, "tab-b").click();

    const url = new URL(window.location.href);
    expect(url.searchParams.get("view")).toBe("b");
  });

  it("selecting the default panel strips ?view= from the URL", async () => {
    history.replaceState(null, "", "/posts/abc?view=b");

    const { root, unmount } = await mountController({
      identifier: "tabs",
      controllerClass: TabsController,
      html: FIXTURE,
    });
    teardown = unmount;

    tab(root, "tab-a").click();

    const url = new URL(window.location.href);
    expect(url.searchParams.has("view")).toBe(false);
  });

  it("uses history.replaceState (not pushState) so back goes to the previous page", async () => {
    const replaceSpy = vi.spyOn(history, "replaceState");
    const pushSpy = vi.spyOn(history, "pushState");

    const { root, unmount } = await mountController({
      identifier: "tabs",
      controllerClass: TabsController,
      html: FIXTURE,
    });
    teardown = unmount;

    tab(root, "tab-c").click();

    expect(replaceSpy).toHaveBeenCalled();
    expect(pushSpy).not.toHaveBeenCalled();
    replaceSpy.mockRestore();
    pushSpy.mockRestore();
  });

  it("End jumps to the last tab; Home returns to the first", async () => {
    const { root, unmount } = await mountController({
      identifier: "tabs",
      controllerClass: TabsController,
      html: FIXTURE,
    });
    teardown = unmount;

    tab(root, "tab-a").dispatchEvent(new KeyboardEvent("keydown", { key: "End", bubbles: true }));
    expect(tab(root, "tab-c").getAttribute("aria-selected")).toBe("true");

    tab(root, "tab-c").dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true }));
    expect(tab(root, "tab-a").getAttribute("aria-selected")).toBe("true");
  });
});
