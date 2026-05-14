import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as Turbo from "@hotwired/turbo";

import SearchController from "../search_controller.ts";
import { mountController } from "../../__specs__/helpers.ts";

const FIXTURE = `
  <label data-controller="search" data-search-delay-value="50">
    <input
      id="topbar-search"
      type="search"
      name="q"
      placeholder="Search"
      data-search-target="input"
      data-action="input->search#query"
    />
    <button
      type="button"
      data-action="click->search#clear"
      data-test="clear"
    >clear</button>
  </label>
`;

function inputOf(root: HTMLElement): HTMLInputElement {
  const input = root.querySelector<HTMLInputElement>("#topbar-search");
  if (!input) throw new Error("fixture missing #topbar-search");
  return input;
}

let teardown: (() => void) | undefined;
let visitSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.useFakeTimers();
  visitSpy = vi.spyOn(Turbo, "visit").mockImplementation(() => {});
  // Each spec writes location via vi.stubGlobal so the controller's
  // ``new URL(window.location.href)`` has a deterministic base.
  vi.stubGlobal("location", new URL("http://localhost/posts"));
});

afterEach(() => {
  teardown?.();
  teardown = undefined;
  visitSpy.mockRestore();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function syntheticInput(input: HTMLInputElement, value: string): Event {
  input.value = value;
  return { currentTarget: input } as unknown as Event;
}

describe("search_controller", () => {
  it("debounces: rapid query() calls trigger one Turbo.visit after the delay", async () => {
    const { root, controller, unmount } = await mountController<SearchController>({
      identifier: "search",
      controllerClass: SearchController,
      html: FIXTURE,
    });
    teardown = unmount;

    const input = inputOf(root);
    controller.query(syntheticInput(input, "go"));
    controller.query(syntheticInput(input, "gol"));
    controller.query(syntheticInput(input, "gold"));

    expect(visitSpy).not.toHaveBeenCalled();

    vi.advanceTimersByTime(60);

    expect(visitSpy).toHaveBeenCalledTimes(1);
    expect(visitSpy).toHaveBeenCalledWith("http://localhost/posts?q=gold", {
      action: "replace",
    });
  });

  it("empty value strips q from the URL", async () => {
    vi.stubGlobal("location", new URL("http://localhost/posts?q=stale"));

    const { root, controller, unmount } = await mountController<SearchController>({
      identifier: "search",
      controllerClass: SearchController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.query(syntheticInput(inputOf(root), ""));
    vi.advanceTimersByTime(60);

    expect(visitSpy).toHaveBeenCalledWith("http://localhost/posts", {
      action: "replace",
    });
  });

  it("clear() empties the input and submits immediately (no debounce)", async () => {
    vi.stubGlobal("location", new URL("http://localhost/posts?q=stale"));

    const { root, controller, unmount } = await mountController<SearchController>({
      identifier: "search",
      controllerClass: SearchController,
      html: FIXTURE,
    });
    teardown = unmount;

    const input = inputOf(root);
    input.value = "stale";

    controller.clear();

    expect(input.value).toBe("");
    expect(document.activeElement).toBe(input);
    expect(visitSpy).toHaveBeenCalledWith("http://localhost/posts", {
      action: "replace",
    });
  });

  it("clicking the clear button dispatches to clear() (regression: scope)", async () => {
    vi.stubGlobal("location", new URL("http://localhost/posts?q=stale"));

    const { root, unmount } = await mountController<SearchController>({
      identifier: "search",
      controllerClass: SearchController,
      html: FIXTURE,
    });
    teardown = unmount;

    const input = inputOf(root);
    input.value = "stale";
    const button = root.querySelector<HTMLButtonElement>("[data-test='clear']");
    if (!button) throw new Error("fixture missing clear button");

    button.click();

    // Proves the button's data-action resolved to the search controller —
    // i.e., the controller's scope reaches the sibling button.
    expect(input.value).toBe("");
    expect(visitSpy).toHaveBeenCalledWith("http://localhost/posts", {
      action: "replace",
    });
  });

  it("Cmd-K focuses and selects the input", async () => {
    const { root, unmount } = await mountController<SearchController>({
      identifier: "search",
      controllerClass: SearchController,
      html: FIXTURE,
    });
    teardown = unmount;

    const input = inputOf(root);
    input.value = "existing";

    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true, cancelable: true }),
    );

    expect(document.activeElement).toBe(input);
    expect(input.selectionStart).toBe(0);
    expect(input.selectionEnd).toBe("existing".length);
  });
});
