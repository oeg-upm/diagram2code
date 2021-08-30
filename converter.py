import argparse
import json

from source.chowlk.transformations import transform_ontology
from source.chowlk.utils import read_drawio_xml


def main(diagram_path, output_path, type, format):

    root = read_drawio_xml(diagram_path)
    ontology_turtle, ontology_xml, namespaces, errors = transform_ontology(root)

    print(json.dumps(errors, sort_keys=True, indent=4))

    file = open(output_path, mode="w")

    if format == "ttl":
        file.write(ontology_turtle)
    elif format == "xml":
        file.write(ontology_xml)
    
    file.close()


    
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Convert an xml conceptualization into an ontology.")
    parser.add_argument("diagram_path", type=str, help="the path where the diagram is located")
    parser.add_argument("output_path", type=str, help="the desired location for the generated ontology")
    parser.add_argument("--type", type=str, default="ontology", help="ontology or rdf data")
    parser.add_argument("--format", type=str, default="ttl", help="file format: ttl or xml")
    args = parser.parse_args()

    main(args.diagram_path, args.output_path, args.type, args.format)
