import { afterEach, describe, expect, it } from "vitest";

import CarouselController from "../carousel_controller.ts";
import { mountController } from "../../__specs__/helpers.ts";

const FIXTURE = `
  <div data-controller="carousel">
    <div data-carousel-target="slide" data-active>1</div>
    <div data-carousel-target="slide">2</div>
    <div data-carousel-target="slide">3</div>

    <span data-carousel-target="counter">1/3</span>

    <button data-carousel-target="prev"
            data-action="click->carousel#prev" hidden>prev</button>
    <button data-carousel-target="next"
            data-action="click->carousel#next">next</button>

    <button data-carousel-target="dot" data-action="click->carousel#go" data-index="0" data-active>1</button>
    <button data-carousel-target="dot" data-action="click->carousel#go" data-index="1">2</button>
    <button data-carousel-target="dot" data-action="click->carousel#go" data-index="2">3</button>
  </div>
`;

const syntheticClick = (target: HTMLElement): Event =>
  ({ currentTarget: target }) as unknown as Event;

function slides(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>('[data-carousel-target="slide"]'));
}

function dots(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>('[data-carousel-target="dot"]'));
}

let teardown: (() => void) | undefined;

afterEach(() => {
  teardown?.();
  teardown = undefined;
});

describe("carousel_controller", () => {
  it("starts at index 0 with prev hidden and counter 1/N", async () => {
    const { root, unmount } = await mountController({
      identifier: "carousel",
      controllerClass: CarouselController,
      html: FIXTURE,
    });
    teardown = unmount;

    const [a, b, c] = slides(root);
    expect(a.hasAttribute("data-active")).toBe(true);
    expect(b.hasAttribute("data-active")).toBe(false);
    expect(c.hasAttribute("data-active")).toBe(false);

    const prev = root.querySelector<HTMLButtonElement>('[data-carousel-target="prev"]')!;
    const next = root.querySelector<HTMLButtonElement>('[data-carousel-target="next"]')!;
    const counter = root.querySelector<HTMLElement>('[data-carousel-target="counter"]')!;
    expect(prev.hidden).toBe(true);
    expect(next.hidden).toBe(false);
    expect(counter.textContent).toBe("1/3");
  });

  it("next() advances; data-active migrates and counter updates", async () => {
    const { root, controller, unmount } = await mountController<CarouselController>({
      identifier: "carousel",
      controllerClass: CarouselController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.next();

    const [a, b, c] = slides(root);
    expect(a.hasAttribute("data-active")).toBe(false);
    expect(b.hasAttribute("data-active")).toBe(true);
    expect(c.hasAttribute("data-active")).toBe(false);

    const counter = root.querySelector<HTMLElement>('[data-carousel-target="counter"]')!;
    expect(counter.textContent).toBe("2/3");
  });

  it("hides next at the last slide and prev at the first", async () => {
    const { root, controller, unmount } = await mountController<CarouselController>({
      identifier: "carousel",
      controllerClass: CarouselController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.next();
    controller.next();

    const prev = root.querySelector<HTMLButtonElement>('[data-carousel-target="prev"]')!;
    const next = root.querySelector<HTMLButtonElement>('[data-carousel-target="next"]')!;
    expect(prev.hidden).toBe(false);
    expect(next.hidden).toBe(true);

    controller.prev();
    controller.prev();
    expect(prev.hidden).toBe(true);
    expect(next.hidden).toBe(false);
  });

  it("go(event) jumps to the slide at data-index", async () => {
    const { root, controller, unmount } = await mountController<CarouselController>({
      identifier: "carousel",
      controllerClass: CarouselController,
      html: FIXTURE,
    });
    teardown = unmount;

    const dot2 = dots(root)[2];
    controller.go(syntheticClick(dot2));

    const [a, b, c] = slides(root);
    expect(a.hasAttribute("data-active")).toBe(false);
    expect(b.hasAttribute("data-active")).toBe(false);
    expect(c.hasAttribute("data-active")).toBe(true);

    const counter = root.querySelector<HTMLElement>('[data-carousel-target="counter"]')!;
    expect(counter.textContent).toBe("3/3");
  });

  it("ArrowRight dispatched on the element advances the slide", async () => {
    const { root, unmount } = await mountController({
      identifier: "carousel",
      controllerClass: CarouselController,
      html: FIXTURE,
    });
    teardown = unmount;

    root.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));

    const [, b] = slides(root);
    expect(b.hasAttribute("data-active")).toBe(true);
  });
});
