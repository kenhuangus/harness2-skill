// Example OpenCode plugin (c8). It acts inside the tool loop.
// Replace the body with a real hook. Keep it deterministic and small.
export const ExamplePlugin = async () => {
  return {
    "tool.execute.after": async (_input, _output) => {
      // No-op placeholder. Add loop-level enforcement here.
    },
  };
};
