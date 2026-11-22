---
type: Concept
title: Menu folders
description: Folders of projects and tags in the sidebar as Super Productivity keeps them in menuTree: shown as groups that open and close, created, renamed, deleted, lists moved into them.
tags: [menu, folders, sidebar, menuTree]
resource: ../pensum/store/menu_tree.py
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
sources:
  - id: sp20
    title: Super Productivity 20.0.0, commit 9980fd76 (2026-11-18)
    url: https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
---

# Menu folders

(#27) The sidebar shows the folders of `menuTree.projectTree` and
`tagTree` as rows that open and close, with their lists indented.
Rules from `menu-tree.model.ts`, `menu-tree.reducer.ts` and
`menu-tree.service.ts`[^sp20]:

- A folder is `{k: "f", id, name, isExpanded, children}`; a folder
  without `isExpanded` is open.
- **New Folder…** (sidebar's add menu): a random UUID, the trimmed name
  (empty adds nothing), open, no children, at the end of the tree.
- **Move to Folder** (a list's menu): the list's node leaves wherever
  it was and goes to the end of the folder, which opens; **No Folder**
  puts it at the end of the tree.
- A folder's menu renames it or deletes it. Deleting removes the folder
  node with its children, as the reducer does; the lists stay in the
  data and are shown after the tree (`Dataset._tree_order`).

Tests: `tests/test_menu_tree.py`, `tests/test_m3_ui.py`.

[^sp20]: Super Productivity 20.0.0 at commit 9980fd76, https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
