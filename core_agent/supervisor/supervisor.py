from typing import Any, Type, Sequence, Literal, Callable
from typing_extensions import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt.chat_agent_executor import AgentState, create_react_agent
from langgraph.utils.runnable import RunnableCallable


OutputMode = Literal["full_history", "last_message"]
"""Mode for adding agent outputs to the message history in the multi-agent workflow

- `full_history`: add the entire agent message history
- `last_message`: add only the last message
"""


def _make_call_agent(
    agent,
    output_mode: OutputMode,
    supervisor_name: str,
) -> Callable[[dict], dict] | RunnableCallable:
    if output_mode not in OutputMode.__args__:
        raise ValueError(
            f"Invalid agent output mode: {output_mode}. Needs to be one of {OutputMode.__args__}"
        )

    def _process_output(output: dict) -> dict:
        messages = output["messages"]
        if output_mode == "full_history":
            pass
        elif output_mode == "last_message":
            messages = messages[-1:]
        else:
            raise ValueError(
                f"Invalid agent output mode: {output_mode}. "
                f"Needs to be one of {OutputMode.__args__}"
            )

        return {
            **output,
            "messages": messages,
        }

    def call_agent(state: dict) -> dict:
        output = agent.invoke(state)
        return _process_output(output)

    async def acall_agent(state: dict) -> dict:
        output = await agent.ainvoke(state)
        return _process_output(output)

    return RunnableCallable(call_agent, acall_agent)


def create_supervisor(
        agents,
        *,
        model,
        supervisor_name: str = "supervisor",
        prompt: str = "",
        state_schema = AgentState,
        config_schema: Type[Any] | None = None,
        output_mode: OutputMode = "last_message",
    ) -> StateGraph:
    """
    Create a multi-agent supervisor.
    """
    agent_names = set()
    for agent in agents:
        agent_names.add(agent.name)
    supervisor_agent = create_react_agent(
        model=model,
        tools=[],
        prompt=prompt,
        state_schema=state_schema
    )
    workflow = StateGraph(state_schema, config_schema=config_schema)
    workflow.add_node(supervisor_agent, destinations=tuple(agent_names) + (END,))
    workflow.add_edge(START, supervisor_agent.name)
    for agent in agents:
        workflow.add_node(
            agent.add_node(
                agent.name,
                _make_call_agent(
                    agent,
                    output_mode,
                    supervisor_name,
                ),
        )
        )
    return workflow