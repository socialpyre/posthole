import { afterEach, beforeEach, describe, expect, it } from "vitest";

import SidebarController from "../sidebar_controller.ts";
import { mountController } from "../../__specs__/helpers.ts";

const ROOT = document.documentElement;
const COLLAPSE_KEY = "posthole:sidebar-collapsed";
const FIXTURE = `<div data-controller="sidebar"></div>`;

type Sidebar = InstanceType<typeof SidebarController>;

let teardown: (() => void) | undefined;

beforeEach(() => {
  localStorage.clear();
  ROOT.removeAttribute("data-drawer-open");
  ROOT.removeAttribute("data-sidebar-collapsed");
});

afterEach(() => {
  teardown?.();
  teardown = undefined;
});

describe("sidebar_controller", () => {
  it("open() sets data-drawer-open on <html>", async () => {
    const { controller, unmount } = await mountController<Sidebar>({
      identifier: "sidebar",
      controllerClass: SidebarController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.open();

    expect(ROOT.hasAttribute("data-drawer-open")).toBe(true);
  });

  it("close() removes data-drawer-open", async () => {
    ROOT.setAttribute("data-drawer-open", "");
    const { controller, unmount } = await mountController<Sidebar>({
      identifier: "sidebar",
      controllerClass: SidebarController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.close();

    expect(ROOT.hasAttribute("data-drawer-open")).toBe(false);
  });

  it("toggleCollapse() from un-collapsed sets the attribute and writes '1' to localStorage", async () => {
    const { controller, unmount } = await mountController<Sidebar>({
      identifier: "sidebar",
      controllerClass: SidebarController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.toggleCollapse();

    expect(ROOT.hasAttribute("data-sidebar-collapsed")).toBe(true);
    expect(localStorage.getItem(COLLAPSE_KEY)).toBe("1");
  });

  it("toggleCollapse() from collapsed clears the attribute and removes the localStorage entry", async () => {
    ROOT.setAttribute("data-sidebar-collapsed", "");
    localStorage.setItem(COLLAPSE_KEY, "1");
    const { controller, unmount } = await mountController<Sidebar>({
      identifier: "sidebar",
      controllerClass: SidebarController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.toggleCollapse();

    expect(ROOT.hasAttribute("data-sidebar-collapsed")).toBe(false);
    expect(localStorage.getItem(COLLAPSE_KEY)).toBeNull();
  });
});
