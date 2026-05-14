import { afterEach, describe, expect, it } from "vitest";

import ListSelectionController from "../list_selection_controller.ts";
import { mountController } from "../../__specs__/helpers.ts";

const FIXTURE = `
  <div data-controller="list-selection" data-inbox-pane="list">
    <a href="/posts/a" data-list-selection-target="row"
       data-action="click->list-selection#select"
       aria-current="page">A</a>

    <a href="/posts/b" data-list-selection-target="row"
       data-action="click->list-selection#select">B</a>

    <a href="/posts/c" data-list-selection-target="row"
       data-action="click->list-selection#select">C</a>
  </div>
`;

function rowFor(root: HTMLElement, id: string): HTMLAnchorElement {
  const a = root.querySelector<HTMLAnchorElement>(`a[href='/posts/${id}']`);
  if (!a) throw new Error(`fixture missing /posts/${id}`);
  return a;
}

const syntheticClick = (target: HTMLAnchorElement): Event =>
  ({ currentTarget: target }) as unknown as Event;

let teardown: (() => void) | undefined;

afterEach(() => {
  teardown?.();
  teardown = undefined;
});

describe("list_selection_controller", () => {
  it("leaves server-rendered aria-current intact on connect", async () => {
    const { root, unmount } = await mountController({
      identifier: "list-selection",
      controllerClass: ListSelectionController,
      html: FIXTURE,
    });
    teardown = unmount;

    expect(rowFor(root, "a").getAttribute("aria-current")).toBe("page");
    expect(rowFor(root, "b").getAttribute("aria-current")).toBe(null);
    expect(rowFor(root, "c").getAttribute("aria-current")).toBe(null);
  });

  it("select() moves aria-current to the clicked row", async () => {
    const { root, controller, unmount } = await mountController<ListSelectionController>({
      identifier: "list-selection",
      controllerClass: ListSelectionController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.select(syntheticClick(rowFor(root, "b")));

    expect(rowFor(root, "b").getAttribute("aria-current")).toBe("page");
    expect(rowFor(root, "a").getAttribute("aria-current")).toBe(null);
    expect(rowFor(root, "c").getAttribute("aria-current")).toBe(null);
  });

  it("select() flips data-inbox-pane from list to detail", async () => {
    const { root, controller, unmount } = await mountController<ListSelectionController>({
      identifier: "list-selection",
      controllerClass: ListSelectionController,
      html: FIXTURE,
    });
    teardown = unmount;

    expect(root.getAttribute("data-inbox-pane")).toBe("list");

    controller.select(syntheticClick(rowFor(root, "b")));

    expect(root.getAttribute("data-inbox-pane")).toBe("detail");
  });

  it("two clicks land aria-current on the most recent", async () => {
    const { root, controller, unmount } = await mountController<ListSelectionController>({
      identifier: "list-selection",
      controllerClass: ListSelectionController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.select(syntheticClick(rowFor(root, "b")));
    controller.select(syntheticClick(rowFor(root, "c")));

    expect(rowFor(root, "c").getAttribute("aria-current")).toBe("page");
    expect(rowFor(root, "b").getAttribute("aria-current")).toBe(null);
    expect(rowFor(root, "a").getAttribute("aria-current")).toBe(null);
  });
});
