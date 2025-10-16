/**
 * Remark plugin to clean and normalize markdown from LLM responses
 * Intelligently transforms code blocks and removes artifacts
 * No external dependencies - uses plain AST traversal
 */
export default function remarkCleanMarkdown() {
  return (tree) => {
    // Helper function to visit all nodes in the AST
    function visit(node, callback, parent = null, index = null) {
      callback(node, index, parent);

      if (node.children && Array.isArray(node.children)) {
        // Visit in reverse to handle node removal safely
        for (let i = node.children.length - 1; i >= 0; i--) {
          visit(node.children[i], callback, node, i);
        }
      }
    }

    visit(tree, (node, index, parent) => {
      // Transform single-line code blocks to inline code
      if (node.type === 'code' && parent && typeof index === 'number') {
        const lines = (node.value || '').split('\n');
        const nonEmptyLines = lines.filter(line => line.trim());

        // If it's a single line of simple text (not actual code), convert to inline
        if (nonEmptyLines.length === 1 && nonEmptyLines[0].length < 100) {
          const value = nonEmptyLines[0].trim();

          // Check if it looks like a simple value (port, path, variable name, etc.)
          // Be conservative - only convert very simple patterns
          const looksLikeSimpleValue =
            /^\d+$/.test(value) || // Just a number (like port 8443)
            /^\/[\w\/\-\.]+$/.test(value) || // File path
            /^[\w\-]+$/.test(value) || // Simple identifier (single word)
            /^[\w\-\.]+:\d+$/.test(value); // host:port

          if (looksLikeSimpleValue) {
            // Replace code block with inline code in a paragraph
            parent.children[index] = {
              type: 'paragraph',
              children: [{
                type: 'inlineCode',
                value: value
              }]
            };
          }
        }
      }

      // Remove paragraphs that contain only punctuation or whitespace
      if (node.type === 'paragraph' && node.children && parent && typeof index === 'number') {
        const textContent = node.children
          .filter(child => child.type === 'text')
          .map(child => child.value)
          .join('');

        if (/^[\s,)}\]]+$/.test(textContent)) {
          parent.children.splice(index, 1);
        }
      }

      // Remove empty paragraphs
      if (node.type === 'paragraph' && parent && typeof index === 'number') {
        if (!node.children || node.children.length === 0) {
          parent.children.splice(index, 1);
        }
      }
    });
  };
}
