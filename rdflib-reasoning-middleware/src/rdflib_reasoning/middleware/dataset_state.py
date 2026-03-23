from langchain.agents.middleware import AgentState


class DatasetState(AgentState):
    """
    State for the dataset middleware.
    """

    # dataset: NotRequired[Dataset]
