from langchain.agents.middleware import AgentState
from rdflib import Dataset


class DatasetState(AgentState):
    """
    State for the dataset middleware.
    """

    dataset: Dataset
