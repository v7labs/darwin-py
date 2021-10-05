window.addEventListener("load", (_event) => {
  const menu = document.querySelector(".wy-menu ul li:first-child")
  recurse(menu)
});

/**
 * Given a Node, it recursively goes through every child and checks if the child is expandable, it
 * expands it unless it is already expanded.
 *
 * @param {Node} node   The node to evaluate.
 */
const recurse = (node) => {
  if (isExpandable(node) && !isExpanded(node)) {
    node.classList.add("current")
  }

  // By default, children are not arrays, so we need to convert them
  children = Array.prototype.slice.call(node.children)

  children.forEach(recurse)
}

/**
 * Returns whether or not the given node is an expandable list.
 *
 * @param {Node} node   The node to evaluate.
 *
 * @returns {boolean} true if the node is a toctree that can be expanded, false otherwise.
 */
const isExpandable = (node) => node.className.includes("toctree-l")

/**
 * Returns whether or not the given expandable node is already expanded.
 * Nodes are considered expandaded if they are 'current'ly selected, so we take advantage of this.
 *
 * @param {Node} node   The node to evaluate.
 *
 * @returns {boolean} true if the node is already expanded, false otherwise.
 */
const isExpanded = (node) => node.classList.contains("current")
