# schema-gen

LinkML schema and documentation generator for FRINK

## Installation

It should be enough to install the contents of the requirements.txt file.

## Usage

### Schema generation

To generate a schema `graph-name.yaml` from a folder `/path/to/graph/data`, run

```
python3 src/dump_yaml.py graph-name /path/to/graph/data
```

The [title](https://linkml.io/linkml-model/latest/docs/title/) of the graph will also be `graph-name`; to override this, supply a graph name after the folder path.

### Documentation generation

To generate Markdown documentation from the resulting `graph-name.yaml` file, run

```
python3 src/docgen-frink.py graph-name.yaml --template-directory src/docgen-frink-templates --directory /path/to/documentation/for/this/graph
```

Some options that are recommended to be enabled:

* `--include-top-level-diagram` to produce an overall class diagram on the top-level README.
* `--diagram-type mermaid_class_diagram` to produce diagrams in the Mermaid format on the README and on each class description page.
* `--no-mergeimports` to prevent the generation of documentation for native LinkML constructs.
* `--subfolder-type-separation` to separate classes and slots into different folders for navigation purposes.
