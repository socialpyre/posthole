import { afterEach, describe, expect, it } from "vitest";

import HelloController from "../hello_controller.ts";
import { mountController } from "../../__specs__/helpers.ts";

let teardown: (() => void) | undefined;

afterEach(() => {
  teardown?.();
  teardown = undefined;
});

describe("hello_controller", () => {
  it("writes 'stimulus loaded' into the output target on connect", async () => {
    const { root, unmount } = await mountController({
      identifier: "hello",
      controllerClass: HelloController,
      html: `<div data-controller="hello"><span data-hello-target="output"></span></div>`,
    });
    teardown = unmount;

    const output = root.querySelector<HTMLElement>("[data-hello-target='output']");
    expect(output?.textContent).toBe("stimulus loaded");
  });
});
