import tempfile
from source.chowlk.finding import *
from source.chowlk.associations import *
from source.chowlk.writer import *
from source.chowlk.utils import *
import rdflib
import os

def transform_ontology(root):
    finder = Finder(root)
    concepts, attribute_blocks, datatypes, relations, individuals, anonymous_concepts, metadata, namespaces, rhombuses, errors = finder.find_elements()
    values = finder.find_attribute_values()
    prefixes_identified = find_prefixes(concepts, relations, attribute_blocks, individuals)
    relations, attribute_blocks = enrich_properties(rhombuses, relations, attribute_blocks, concepts)
    attribute_blocks = resolve_concept_reference(attribute_blocks, concepts)
    associations = concept_attribute_association(concepts, attribute_blocks)
    associations, relations = concept_relation_association(associations, relations)
    individuals = individual_type_identification(individuals, associations, relations)

    individuals = individual_type_identification_rdf(individuals, concepts, relations)
    associations_individuals = individual_relation_association(individuals, relations)
    associations_individuals = individual_attribute_association(associations_individuals, values, relations)

    file, onto_prefix, onto_uri, new_namespaces = get_ttl_template(namespaces, prefixes_identified)
    file = write_ontology_metadata(file, metadata, onto_uri)
    file = write_ontology_datatypes(file, datatypes)
    file = write_object_properties(file, relations, concepts, anonymous_concepts, attribute_blocks)
    file = write_data_properties(file, attribute_blocks, concepts)
    file = write_concepts(file, concepts, anonymous_concepts, associations)
    file = write_instances(file, individuals)
    file = write_triplets(file, individuals, associations_individuals, values)
    file = write_general_axioms(file, concepts, anonymous_concepts)

    file.seek(os.SEEK_SET)

    g = rdflib.Graph()
    g.parse(data=file.read(), format="turtle")

    turtle_output_file = tempfile.NamedTemporaryFile()
    xml_output_file = tempfile.NamedTemporaryFile()

    g.serialize(destination=turtle_output_file, format="turtle")
    g.serialize(destination=xml_output_file, format="xml")

    turtle_output_file.seek(0)
    xml_output_file.seek(0)

    turtle_string = turtle_output_file.read().decode("utf-8")
    xml_string = xml_output_file.read().decode("utf-8")

    return turtle_string, xml_string, new_namespaces, errors


def transform_rdf(root):

    finder = Finder(root)
    individuals = finder.find_individuals()
    relations = finder.find_relations()
    namespaces = finder.find_namespaces()
    values = finder.find_attribute_values()
    concepts, attribute_blocks = finder.find_concepts_and_attributes()

    prefixes_identified = find_prefixes(concepts, relations, attribute_blocks, individuals)

    individuals = individual_type_identification_rdf(individuals, concepts, relations)
    
    associations_individuals = individual_relation_association(individuals, relations)
    associations_individuals = individual_attribute_association(associations_individuals, values, relations)
    file, onto_prefix, onto_uri, new_namespaces = get_ttl_template(namespaces, prefixes_identified)

    file = write_triplets(file, individuals, associations_individuals, values)

    file.seek(os.SEEK_SET)

    g = rdflib.Graph()
    g.parse(data=file.read(), format="turtle")

    turtle_output_file = tempfile.NamedTemporaryFile()
    xml_output_file = tempfile.NamedTemporaryFile()

    g.serialize(destination=turtle_output_file, format="turtle")
    g.serialize(destination=xml_output_file, format="xml")

    turtle_output_file.seek(0)
    xml_output_file.seek(0)

    turtle_string = turtle_output_file.read().decode("utf-8")
    xml_string = xml_output_file.read().decode("utf-8")

    return turtle_string, xml_string