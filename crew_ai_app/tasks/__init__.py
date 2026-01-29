"""Tasks package for dispute resolution workflow.

Note: In this implementation, tasks are primarily integrated into agent methods
rather than standalone CrewAI Task objects, as the workflow is fairly linear
and agent-specific.
"""

# TODO: If complex multi-agent orchestration is needed in the future,
# individual Task classes can be added here for more granular control