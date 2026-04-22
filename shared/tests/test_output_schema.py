
import pytest
from automatia_shared.contracts.ui_contract import (
    OutputField, OutputSchema, DataContract, InputType, Constraints, UIContract, InputDefinition
)

class TestOutputSchema:
    def test_output_schema_serialization(self):
        """Test basic serialization of OutputSchema."""
        schema = OutputSchema(fields=[
            OutputField(
                name="result_path",
                label="Result Path",
                type=InputType.FILE,
                description="Path to the generated file"
            ),
            OutputField(
                name="count",
                label="Count",
                type=InputType.INT,
                constraints=Constraints(min=0)
            )
        ])
        
        data = schema.model_dump()
        assert len(data["fields"]) == 2
        assert data["fields"][0]["name"] == "result_path"
        assert data["fields"][1]["name"] == "count"
        assert data["fields"][1]["constraints"]["min"] == 0

    def test_to_json_schema(self):
        """Test generation of JSON Schema from OutputSchema."""
        schema = OutputSchema(fields=[
            OutputField(name="name", label="Name", type=InputType.STR),
            OutputField(name="age", label="Age", type=InputType.INT, constraints=Constraints(min=18)),
            OutputField(name="optional", label="Opt", type=InputType.STR, nullable=True)
        ])

        json_schema = schema.to_json_schema()
        
        assert json_schema["type"] == "object"
        assert "name" in json_schema["properties"]
        assert "age" in json_schema["properties"]
        assert json_schema["properties"]["age"]["type"] == "integer"
        assert json_schema["properties"]["age"]["minimum"] == 18
        
        # Check required fields (nullable=False by default)
        assert "name" in json_schema["required"]
        assert "age" in json_schema["required"]
        assert "optional" not in json_schema["required"]

class TestDataContract:
    def test_data_contract_structure(self):
        """Test full DataContract structure."""
        contract = DataContract(
            inputs=UIContract(inputs=[
                InputDefinition(name="source_file", label="Source", type=InputType.FILE)
            ]),
            outputs=OutputSchema(fields=[
                OutputField(name="processed_file", label="Target", type=InputType.FILE)
            ])
        )
        
        assert len(contract.inputs.inputs) == 1
        assert len(contract.outputs.fields) == 1
        assert contract.version == "1.0.0"
