import tempfile
from app.source.chowlk.resources.anonymousClass import *
from app.source.chowlk.resources.properties import *
from app.source.chowlk.resources.utils import base_directive_prefix
from app.source.chowlk.resources.anonymousIndividual import get_anonymous_individual, parse_data_value, write_annotation_triple

class Writer_model():

    def __init__(self):
        self.file = tempfile.TemporaryFile(mode='w+', encoding="utf-8")

    def write_ontology(self, diagram_model, prefixes_identified, associations, associations_individuals):
        base_uri, new_namespaces = self.write_prefixes(diagram_model, prefixes_identified)

        ontology_uri = diagram_model.get_ontology_uri()

        if not ontology_uri:
            diagram_model.set_ontology_uri(base_uri)
            diagram_model.generate_warning("An ontology uri has not been declared. The base uri has been taken as the ontology uri", None, None, "Ontology")

        self.write_ontology_metadata(diagram_model)
        self.write_object_properties(diagram_model)
        self.write_data_properties(diagram_model)
        self.write_concepts(diagram_model, associations)
        self.write_instances(diagram_model)
        self.write_triplets(diagram_model, associations_individuals)
        self.write_general_axioms(diagram_model)

        return self.file, new_namespaces, base_uri


    def write_prefixes(self, diagram_model, prefixes_identified):
        # Get neccesary attributes
        namespaces = diagram_model.get_namespaces()

        # Create default prefixes
        namespaces['owl'] = 'http://www.w3.org/2002/07/owl#'
        namespaces['rdf'] = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        namespaces['rdfs'] = 'http://www.w3.org/2000/01/rdf-schema#'
        namespaces['xml'] = 'http://www.w3.org/XML/1998/namespace'
        namespaces['xsd'] = 'http://www.w3.org/2001/XMLSchema#'
        namespaces['dc'] = 'http://purl.org/dc/elements/1.1/'
        namespaces['dcterms'] = 'http://purl.org/dc/terms/'
        namespaces['vann'] = 'http://purl.org/vocab/vann/'
        namespaces['mod'] = 'https://w3id.org/mod#'

        new_namespaces = create_prefix_not_declared(prefixes_identified, namespaces)

        prefixes, base_uri, base_prefix, empty_prefix = find_base_and_empty_prefix(namespaces, diagram_model)

        # Check if the user has defined "@base"
        if(not base_uri):
            base_prefix, base_uri = select_base(namespaces, new_namespaces)
            diagram_model.generate_warning("A base has not been declared. The first namespace has been taken as base", None, None, "Base")
        
        if check_valid_prefix(base_uri):
            base_uri += '/'
            diagram_model.generate_error("The base uri must end with '#' or '/'. The '/' has been added to the end of the base uri", None, None, "Base")
        
        # If the user has not declared the empty prefix in namespace => Add empty prefix with same uri as @base
        if(not empty_prefix):
            empty_prefix = base_uri

        # Write empty prefix (the empty prefix has to be above the other prefixes in order to be correctly detected by rdflib)
        self.file.write("@prefix : <" + empty_prefix + "> .\n")

        # Write defined prefixes
        for prefix in prefixes:
            self.file.write(prefix)

        # Write not defined namespaces
        for prefix, uri in new_namespaces.items():
            self.file.write("@prefix " + prefix + ": <" + uri + "> .\n")

        # Write base
        self.file.write("@base <" + base_uri + "> .\n\n")

        return base_uri, new_namespaces
    
    # This function writes the declaration of the ontology uri, writes the ontology metadata 
    # and writes the declaration of the annotation properties used in the metadata
    def write_ontology_metadata(self, diagram_model):
        # Get neccesary attributes
        metadata = diagram_model.get_metadata()
        onto_uri = diagram_model.get_ontology_uri()

        # Write annotation properties used in order to declare the ontology metadata
        annotation_properties = ''

        # Has the user defined the ontology uri correctly?
        if not check_is_uri(onto_uri):
            onto_uri = "<" + onto_uri + ">"

        # Write ontology uri
        self.file.write(onto_uri + " rdf:type owl:Ontology")

        # For each ontology metadata write its corresponding value
        for prefix, values in metadata.items():

            for value in values:
                self.file.write(" ;\n")

                # Is a special type of metadata?
                if "imports" in prefix:

                    # Has the user defined the object between <>?
                    if not check_is_uri(value):
                        value = "<" + value + ">"

                    self.file.write("\t\t\t" + prefix + " " + value)

                else:

                    annotation_properties += f'{prefix} a owl:AnnotationProperty .\n\n'

                    # Does it have a datatype defined?
                    if "^^" in value:
                        self.file.write("\t\t\t" + prefix + " " + value)
                    
                    # It is defined as an uri?
                    elif check_is_uri(value):
                        self.file.write("\t\t\t" + prefix + " " + value)

                    # It is defined a literal?
                    elif '@' in value or '"' in value:
                        self.file.write("\t\t\t" + prefix + " " + value)

                    else:
                        # It is assumed the datatype is a literal
                        value = "\"" + value + "\""
                        self.file.write("\t\t\t" + prefix + " " + value)
                    
        self.file.write(" ;\n")
        self.file.write("\t\t\t" + "mod:createdWith <https://chowlk.linkeddata.es/>")
        self.file.write(" .\n\n")
        self.file.write(annotation_properties)

    # This function writes the declaration of the object properties, its relations with other object properties
    # (i.e. owl:equivalentProperty, rdfs:subPropertyOf, etc.), the additional types of the object properties
    # (i.e. owl:InverseFunctionalProperty, etc.), its domain and range and annotations.
    # Aditionally, it writes the declaration of the annotation properties declared by the user using rhombuses.
    # Aditionally, it writes the declaration of the functional properties which has not been identified as datatype properties
    # or object properties.
    def write_object_properties(self, diagram_model):
        # Get neccesary attributes
        relations = diagram_model.get_arrows()
        concepts = diagram_model.get_classes()
        anonymous_concepts = diagram_model.get_ellipses()
        attribute_blocks = diagram_model.get_datatype_properties()
        hexagons = diagram_model.get_hexagons()
        individuals = diagram_model.get_individuals()
        anonymous_classes = diagram_model.get_anonymous_classes()
        uri_references = diagram_model.get_uri_references()
        values = diagram_model.get_property_values()
        anonymous_individuals = diagram_model.get_anonymous_individuals()

        self.file.write("#################################################################\n"
                "#    Object Properties\n"
                "#################################################################\n\n")

        # Iterate the arrows and rhombuses (relations) detected in the diagram
        for relation_id, relation in relations.items():

            if "type" not in relation:
                continue

            # Has the relation been detected as an object property?
            if relation["type"] == "owl:ObjectProperty":
                property_uri = relation["uri"]
                property_prefix = base_directive_prefix(relation["prefix"])
                # Write object property declaration
                self.file.write("### " + property_prefix + property_uri + "\n")
                self.file.write(property_prefix + property_uri + " rdf:type owl:ObjectProperty")

                # Is the object property deprecated?
                if relation['deprecated']:
                    self.file.write(", owl:DeprecatedProperty")             

                # Write additional types
                # Is the object property defined as functional?
                if relation["functional"]:
                    self.file.write(" ,\n")
                    self.file.write("\t\t\towl:FunctionalProperty")

                # Is the object property defined as symmetric?
                if relation["symmetric"]:
                    self.file.write(" ,\n")
                    self.file.write("\t\t\towl:SymmetricProperty")

                # Is the object property defined as transitive?
                if relation["transitive"]:
                    self.file.write(" ,\n")
                    self.file.write("\t\t\towl:TransitiveProperty")

                # Is the object property defined as inverse functional?
                if relation["inverse_functional"]:
                    self.file.write(" ,\n")
                    self.file.write("\t\t\towl:InverseFunctionalProperty")
                
                # Is the object property defined as reflexive?
                if relation["reflexive"]:
                    self.file.write(" ,\n")
                    self.file.write("\t\t\towl:ReflexiveProperty")

                # Is the object property defined as asymmetric?
                if relation["asymmetric"]:
                    self.file.write(" ,\n")
                    self.file.write("\t\t\towl:AsymmetricProperty")

                # Is the object property defined as irreflexive?
                if relation["irreflexive"]:
                    self.file.write(" ,\n")
                    self.file.write("\t\t\towl:IrreflexiveProperty")

                # Are annotation defined for this object property?
                if 'annotation' in relation:

                    # For each annotation whose subject is the object property, check if the annotation is valid and write it
                    for annotation in relation['annotation']:
                        text = write_annotation_triple(annotation, relations[annotation], individuals, uri_references, values, diagram_model)

                        # Is the annotation valid?
                        if text:
                            self.file.write(" ;\n")
                            self.file.write(text)

                # Does the object property have a defined domain?
                if "domain" in relation and relation["domain"]:
                    range = relation["range"] if 'range' in relation else ''
                    domain_name = properties_domain_range(relation_id, property_prefix, property_uri, relation["domain"], range, "object property", "domain", concepts, hexagons, diagram_model, individuals, anonymous_concepts, anonymous_classes, relations, attribute_blocks, anonymous_individuals)

                    # Avoid blank nodes
                    if domain_name != ":":
                        self.file.write(" ;\n")
                        self.file.write("\t\trdfs:domain " + domain_name)

                # Does the object property have a defined range? (avoid has value restrictions)
                if "range" in relation and relation["range"] and not relation["hasValue"]:
                    domain = relation["domain"] if 'domain' in relation else ''
                    range_name = properties_domain_range(relation_id, property_prefix, property_uri, relation["range"], domain, "object property", "range", concepts, hexagons, diagram_model, individuals, anonymous_concepts, anonymous_classes, relations, attribute_blocks, anonymous_individuals)

                    # Avoid blank nodes
                    if range_name != ":":
                        self.file.write(" ;\n")
                        self.file.write("\t\trdfs:range " + range_name)

                # Write relations with other object properties.
                # Has the object property been defined as a sub-property of another object property?
                if "rdfs:subPropertyOf" in relation:
                    # Join all the objects of the triple (each object is separated by a comma)
                    triple = ','.join(relation['rdfs:subPropertyOf'])
                    self.file.write(" ;\n")
                    self.file.write("\t\trdfs:subPropertyOf " + triple)

                # Has the object property been defined as the inverse of another object property?
                if "owl:inverseOf" in relation:
                    # Join all the objects of the triple (each object is separated by a comma)
                    triple = ','.join(relation['owl:inverseOf'])
                    self.file.write(" ;\n")
                    self.file.write("\t\towl:inverseOf " + triple)

                # Has the object property been defined as equivalent to another object property?
                if "owl:equivalentProperty" in relation:
                    # Join all the objects of the triple (each object is separated by a comma)
                    triple = ','.join(relation['owl:equivalentProperty'])
                    self.file.write(" ;\n")
                    self.file.write("\t\towl:equivalentProperty " + triple)
                
                # Has the object property been defined as disjoint from another object property?
                if "owl:propertyDisjointWith" in relation:
                    # Join all the objects of the triple (each object is separated by a comma)
                    triple = ','.join(relation['owl:propertyDisjointWith'])
                    self.file.write(" ;\n")
                    self.file.write("\t\towl:propertyDisjointWith " + triple)
                
                # Has the object property been defined as a property chain axiom?
                if 'owl:propertyChainAxiom' in relation:

                    for propertyChain in relation["owl:propertyChainAxiom"]:
                        self.file.write(" ;\n")
                        text = obtain_elements_property_chain(diagram_model, relations, propertyChain)
                        self.file.write("\t\towl:propertyChainAxiom ( " + text + ")")
                    
                # Write label
                self.file.write(" ;\n")
                self.file.write("\t\trdfs:label \"" + relation["label"] + "\"")
                self.file.write(" .\n\n")

            # Has the relation been defined as a functional property?
            elif relation["type"] == "owl:FunctionalProperty":
                # In this case the user has defined in a rhombus a property which has been declared just as functional,
                # and that property has not been used neither as an object property nor datatype property
                uri = relation["uri"]
                prefix = base_directive_prefix(relation["prefix"])
                # Write functional property delcaration
                self.file.write("### " + prefix + uri + "\n")
                self.file.write(prefix + uri + " rdf:type owl:FunctionalProperty")
                
                # Is the functional property deprecated?
                if relation['deprecated']:
                    self.file.write(", owl:DeprecatedProperty")
    
                self.file.write(" ;\n")
                self.file.write("\t\trdfs:label \"" + relation["label"] + "\"")
                self.file.write(" .\n\n")

            # Has the relation been defined as an annotation property?
            elif relation["type"] == "owl:AnnotationProperty":
                self.write_annotation_properties(relation_id, relation, diagram_model)

    # Write annotation properties declaration
    def write_annotation_properties(self, relation_id, relation, diagram_model):
        uri = relation["uri"]
        prefix = base_directive_prefix(relation["prefix"])

        # Write the annotation property declaration
        self.file.write("### " + prefix + uri + "\n")
        self.file.write(prefix + uri + " rdf:type owl:AnnotationProperty")
        self.file.write(" ;\n")
        self.file.write("\t\trdfs:label \"" + relation["label"] + "\"")
        self.file.write(" .\n\n")

        # A domain can not be defined in an annotation property 
        if "domain" in relation and relation["domain"]:
            diagram_model.generate_error("A domain is defined in an annotation property", relation_id, prefix + uri, "Annotation Properties")
        
        # A range can not be defined in an annotation property 
        if "range" in relation and relation["range"] and not relation["hasValue"]:
            diagram_model.generate_error("A range is defined in an annotation property", relation_id, prefix + uri, "Annotation Properties")
    
    # This function writes the declaration of the datatype properties properties, its relations with other datatype properties
    # (i.e. owl:equivalentProperty, rdfs:subPropertyOf, etc.), the additional types of the datatype properties
    # (i.e. owl:InverseFunctionalProperty, etc.), its domain and range and annotations.
    def write_data_properties(self, diagram_model):
        # Get neccesary attributes
        attribute_blocks = diagram_model.get_datatype_properties()
        concepts = diagram_model.get_classes()
        hexagons = diagram_model.get_hexagons()
        values = diagram_model.get_property_values()
        individuals = diagram_model.get_individuals()
        anonymous_concepts = diagram_model.get_ellipses()
        anonymous_classes = diagram_model.get_anonymous_classes()
        relations = diagram_model.get_arrows()
        uri_references = diagram_model.get_uri_references()
        anonymous_individuals = diagram_model.get_anonymous_individuals()
        
        self.file.write("#################################################################\n"
                "#    Data Properties\n"
                "#################################################################\n\n")

        # Iterate the datatype property boxes detected in the diagram
        for id, attribute_block in attribute_blocks.items():

            # Iterate the datatype properties defined in each box
            for attribute in attribute_block["attributes"]:
                uri = attribute["uri"]
                prefix = base_directive_prefix(attribute["prefix"])

                # Write the datatype property declaration
                self.file.write("### " + prefix + uri + "\n")
                self.file.write(prefix + uri + " rdf:type owl:DatatypeProperty")

                # Is the dataype property deprecated?
                if attribute['deprecated']:
                    self.file.write(", owl:DeprecatedProperty")

                # Write additional types
                # Is the datatype property defined as functional?
                if attribute["functional"]:
                    self.file.write(" ,\n")
                    self.file.write("\t\t\towl:FunctionalProperty")

                # Are annotation defined for this datatype property?
                if 'annotation' in attribute:

                    # For each annotation whose subject is the datatype property, check if the annotation is valid and write it
                    for annotation in attribute['annotation']:
                        text = write_annotation_triple(annotation, relations[annotation], individuals, uri_references, values, diagram_model)
                        
                        # Is the annotation valid?
                        if text:
                            self.file.write(" ;\n")
                            self.file.write(text)
                
                # Does the datatype property have a defined domain?
                if attribute["domain"]:

                    # We want to skip the domain definition of those datatype properties block that are below a blank node
                    if not ('concept_associated' in attribute_block and attribute["domain"] == attribute_block['concept_associated'] and attribute["domain"] in anonymous_classes):
                        domain_name = properties_domain_range(id, prefix, uri, attribute["domain"], '', "datatype property", "domain", concepts, hexagons, diagram_model, individuals, anonymous_concepts, anonymous_classes, relations, attribute_blocks, anonymous_individuals)
                        # Avoid blank nodes
                        if domain_name != ":":
                            self.file.write(" ;\n")
                            self.file.write("\t\trdfs:domain " + domain_name)

                # Does the datatype property have a defined range? (avoid has value restrictions)
                if attribute["range"] and not attribute["hasValue"]:
                    
                    # Is the datatype property connected to an hexagon?
                    if attribute["range"] in hexagons:
                        # The user is defining an enumerated datatype.
                        # In this case, the user has declared the datatype property through a rhombus,
                        # which is connected to an hexagon through an arrow whose name is "rdfs:range".
                        hexagon_id = attribute["range"]
                        hexagon = hexagons[hexagon_id]

                        # Is the user defining an enumerated datatype?
                        if hexagon["type"] == "owl:oneOf":
                            self.file.write(" ;\n")
                            self.file.write("\t\trdfs:range [ rdf:type rdfs:Datatype ; owl:oneOf")
                            text1 =""
                            text2 =""
                            # the range is an enumerated datatype
                            enumerated_datatypes_ids = hexagon["group"]

                            # Iterate the elements connected to the hexagon
                            for enumerated_datatypes_id in enumerated_datatypes_ids:

                                # Is the element a data value?
                                if enumerated_datatypes_id in values:

                                    # Is a datatype specified in the data value?
                                    if values[enumerated_datatypes_id]["type"] is not None:

                                        # Is the datatype specified through a prefix:uri?
                                        if ":" in values[enumerated_datatypes_id]["type"]:
                                            object = "\"" + values[enumerated_datatypes_id]["value"] + "\"" + "^^" + values[enumerated_datatypes_id]["type"]
                                        
                                        else:
                                            # The default prefix is xsd
                                            object = "\"" + values[enumerated_datatypes_id]["value"] + "\"" + "^^xsd:" + values[enumerated_datatypes_id]["type"]
                                    
                                    # Is a language specified in the data value?
                                    elif values[enumerated_datatypes_id]["lang"] is not None:
                                        # The data value is a literal
                                        object = "\"" + values[enumerated_datatypes_id]["value"] + "\"" + "@" + values[enumerated_datatypes_id]["lang"]
                                    
                                    else:
                                        # The data value is a literal
                                        object = "\"" + values[enumerated_datatypes_id]["value"] + "\""
                                    
                                    text1 = text1 + "[ rdf:type rdf:List ; rdf:first " + object + "; rdf:rest"
                                    text2 = text2 + " ]"

                                else:
                                    diagram_model.generate_error("An element of an owl:oneOf is not a data value", enumerated_datatypes_id, None, "oneOf")

                            text1 = text1 + " rdf:nil"
                            text2 = text2 + " ]"
                            self.file.write(text1 + text2)

                        else:
                            # The user has defined an invalid hexagon
                            diagram_model.generate_error("The range of a datatype property is not a datatype or an enumerated datatype", hexagon_id, hexagon["type"], "Attributes")

                    # Is the user defining a datatype?
                    elif attribute["datatype"]:
                        prefix = base_directive_prefix(attribute["prefix_datatype"])
                        self.file.write(" ;\n")
                        self.file.write("\t\trdfs:range " + prefix + attribute["datatype"])

                    else:
                        # In this case, the user has declared the datatype property through a rhombus,
                        # which is connected to another element through an arrow whose name is "rdfs:range".
                        diagram_model.generate_error("The range of a datatype property is not a datatype or an enumerated datatype", id, f'{prefix}{uri}', "Attributes")

                # Write relations with other datatype properties
                # Has the datatype property been defined as a sub-property of another datatype property?
                if "rdfs:subPropertyOf" in attribute:
                    # Join all the objects of the triple (each object is separated by a comma)
                    triple = ','.join(attribute['rdfs:subPropertyOf'])
                    self.file.write(" ;\n")
                    self.file.write("\t\trdfs:subPropertyOf " + triple)

                # Has the datatype property been defined as equivalent to another datatype property?
                if "owl:equivalentProperty" in attribute:
                    # Join all the objects of the triple (each object is separated by a comma)
                    triple = ','.join(attribute['owl:equivalentProperty'])
                    self.file.write(" ;\n")
                    self.file.write("\t\towl:equivalentProperty " + triple)
                
                # Has the datatype property been defined as disjoint from another datatype property?
                if "owl:propertyDisjointWith" in attribute:
                    # Join all the objects of the triple (each object is separated by a comma)
                    triple = ','.join(attribute['owl:propertyDisjointWith'])
                    self.file.write(" ;\n")
                    self.file.write("\t\towl:propertyDisjointWith " + triple)

                # Write label
                self.file.write(" ;\n")
                self.file.write("\t\trdfs:label \"" + attribute["label"] + "\"")
                self.file.write(" .\n\n")
    
    # This function writes the declaration of the classes, its class axioms
    # (i.e. owl:subClassOf, owl:equivalentClass.), and annotations.
    def write_concepts(self, diagram_model, associations):
        # Get neccesary attributes
        concepts = diagram_model.get_classes()
        anonymous_concepts = diagram_model.get_ellipses()
        individuals = diagram_model.get_individuals()
        hexagons = diagram_model.get_hexagons()
        anonymous_classes = diagram_model.get_anonymous_classes()
        uri_references = diagram_model.get_uri_references()
        values = diagram_model.get_property_values()
        all_relations = diagram_model.get_arrows()
        
        self.file.write("#################################################################\n"
                "#    Classes\n"
                "#################################################################\n\n")

        # Iterate the classes
        for concept_id, association in associations.items():

            concept = association["concept"]
            concept_prefix = base_directive_prefix(concept["prefix"])
            concept_uri = concept["uri"]

            # Is it a named class?
            if concept_uri == "":
                # This should not happen
                continue

            # Write class declaration
            self.file.write("### " + concept_prefix + concept_uri + "\n")
            self.file.write(concept_prefix + concept_uri + " rdf:type owl:Class")

            # Is the class deprecated?
            if concept['deprecated']:
                self.file.write(", owl:DeprecatedClass") 

            self.file.write(' ;\n')
            self.file.write("\trdfs:label \"" + concept["label"] + "\"")

            attribute_blocks = association["attribute_blocks"]
            relations = association["relations"]
            
            # Iterate the arrows whose source is the class
            for relation_id, relation in relations.items():

                if "type" not in relation:
                    continue

                # Is the arrow an object property?
                if relation["type"] == "owl:ObjectProperty":
                    # The user may be defining a restriction 
                    text, more_than_two_restrictions = restrictions(relation, concepts, diagram_model, hexagons, anonymous_concepts, individuals, all_relations, anonymous_classes, relation_id, [])
                    # Is the user defining a restriction?
                    if text != "":
                        self.file.write(" ;\n")
                        self.file.write("\t" + relation["predicate_restriction"] + "\n")
                        self.file.write(text)
                    
                        if more_than_two_restrictions:
                            prefix = base_directive_prefix(relation["prefix"])
                            diagram_model.generate_warning("More than one restriction has been defined at the same time. This is not an official notation, but we have generated the restriction anyway", relation_id, f'{prefix}{relation["uri"]}', "Restrictions")
                    
                # Is the arrow an annotation property?
                elif relation["type"] == "owl:AnnotationProperty":
                    text = write_annotation_triple(relation_id, relation, individuals, uri_references, values, diagram_model)
                    
                    # Is the annotation valid?
                    if text:
                        self.file.write(" ;\n")
                        self.file.write(text)

                # Is the arrow a class axiom? (i.e. rdfs:subClassOf, owl:disjointWith or owl:equivalentClass)
                elif relation["type"] == "rdfs:subClassOf" or relation['type'] == 'owl:disjointWith' or relation['type'] == 'owl:equivalentClass':
            
                    # Is the object a named class?
                    if relation["target"] in concepts:
                        target_id = relation["target"]
                        target_prefix = base_directive_prefix(concepts[target_id]["prefix"])
                        self.file.write(" ;\n")
                        self.file.write(f'\t{relation["type"]} {target_prefix}{concepts[target_id]["uri"]}')

                    # Is the object an enumerated class? (i.e. owl:oneOf)
                    elif relation["target"] in hexagons:
                        complement = hexagons[relation["target"]]
                        self.file.write(" ; \n")
                        self.file.write(f'\t{relation["type"]} [ rdf:type owl:Class ;')
                        text =  one_of(complement, individuals, diagram_model)
                        self.file.write(text)
                        self.file.write("\t\t]")

                    # Is the object an intersection or an union of classes? (i.e. owl:unionOf or owl:intersectionOf)
                    elif relation["target"] in anonymous_concepts:
                        complement = anonymous_concepts[relation["target"]]

                        # Is the object an intersection of classes?
                        if complement["type"] == "owl:intersectionOf":
                            self.file.write(" ;")
                            self.file.write(f'\t{relation["type"]} [ rdf:type owl:Class ;')
                            text = intersection_of(complement, concepts, diagram_model, hexagons, anonymous_concepts, individuals, all_relations, anonymous_classes, [])
                            self.file.write(text)
                            self.file.write("\t\t]")

                        # Is the object an union of classes?
                        elif complement["type"] == "owl:unionOf":
                            self.file.write(" ;")
                            self.file.write(f'\t{relation["type"]} [ rdf:type owl:Class ;')
                            text = union_of(complement, concepts, diagram_model, hexagons, anonymous_concepts, individuals, all_relations, anonymous_classes, [])
                            self.file.write(text)
                            self.file.write("\t\t]")

                    # Is the object a restriction or a complement class? (i.e. restriction or owl:complementOf)
                    elif relation["target"] in anonymous_classes:
                        # In this case, the target of the arrow is a blank node which is the source of another arrow
                        # (we are just interested in those arrows)
                        complement_id = anonymous_classes[relation["target"]]["relations"]
                        
                        # Is the blank node the source of an arrow?
                        if len(complement_id) > 0:
                            # Get the arrow
                            complement = all_relations[complement_id[0]]

                            # Is the object a restriction?
                            if(complement["type"] == "owl:ObjectProperty"):
                                text, more_than_two_restrictions = restrictions(complement, concepts, diagram_model, hexagons, anonymous_concepts, individuals, all_relations, anonymous_classes, complement_id[0], [])
                                if text != "":
                                    self.file.write(" ;")
                                    self.file.write(f'\t{relation["type"]} ')
                                    self.file.write(text)
                                
                                    if more_than_two_restrictions:
                                        prefix = base_directive_prefix(complement["prefix"])
                                        diagram_model.generate_warning("More than one restriction has been defined at the same time. This is not an official notation, but we have generated the restriction anyway", complement_id[0], f'{prefix}{complement["uri"]}', "Restrictions")
                                

                            # Is the object a complement class?
                            elif(complement["type"] == "owl:complementOf"):
                                text = complement_of(complement, concepts, diagram_model, hexagons, anonymous_concepts, individuals, all_relations, anonymous_classes, [])

                                if text != "":
                                    self.file.write(" ;")
                                    self.file.write(f'\t{relation["type"]} [ rdf:type owl:Class ;')
                                    self.file.write(text)
                                    self.file.write("\t\t]")
                
                # Check errors
                # Is the user connecting an invalid arrow to a complement class?
                elif relation["type"] == "owl:complementOf":
                    diagram_model.generate_error("A class is connected to a owl:complementOf directly. A owl:complementOf can be connected to a class through a class axiom", concept_id, f'{concept_prefix}{concept_uri}', "complementOf")

                # Is the user connecting an invalid arrow to an enumerated class? (i.e. owl:oneOf)
                elif relation["type"] == "rdf:type" and relation["target"] in hexagons:
                    diagram_model.generate_error("A class is connected to a owl:oneOf through a rdf:type. A owl:oneOf can be connected to a class through a class axiom", concept_id, f'{concept_prefix}{concept_uri}', "oneOf")

                # Is the user connecting an invalid arrow to an anonymous class? (i.e. owl:intersectionOf or owl:unionOf)
                elif relation["type"] == "rdf:type" and relation["target"] in anonymous_concepts:
                    target_id = relation["target"]
                    complement = anonymous_concepts[target_id]

                    if complement["type"] == "owl:intersectionOf":
                        diagram_model.generate_error("A class is connected to a owl:intersectionOf through a rdf:type. A owl:intersectionOf can be connected to a class through a class axiom", concept_id, f'{concept_prefix}{concept_uri}', "intersectionOf")
    
                    elif complement["type"] == "owl:unionOf":
                        diagram_model.generate_error("A class is connected to a owl:unionOf through a rdf:type. A owl:unionOf can be connected to a class through a class axiom", concept_id, f'{concept_prefix}{concept_uri}', "unionOf")

            # Iterate the datatype property blocks which are below the class    
            for block_id, attribute_block in attribute_blocks.items():

                # Iterate the datatype properties which are defined in each datatype property block 
                for attribute in attribute_block["attributes"]:

                    text, more_than_two_restrictions = datatype_property_restriction(attribute, diagram_model, block_id)
                    if text != '':
                        self.file.write(f' ;\n\t{attribute["predicate_restriction"]} \n{text}')
                    
                        if more_than_two_restrictions:
                            prefix = base_directive_prefix(attribute["prefix"])
                            diagram_model.generate_warning("More than one restriction has been defined at the same time. This is not an official notation, but we have generated the restriction anyway", block_id, f'{prefix}{attribute["uri"]}', "Restrictions")
                    

            # Iterate all the ellipses.
            # In this case we are searching for the ellipses which define an owl:disjointWith or owl:equivalentClass statement.
            for blank_id, blank in anonymous_concepts.items():
                # These special types of ellipses just have 2 arrows
                if len(blank["group"]) > 2:
                    continue

                # Is the class connected to one of the ellipses we are looking for?
                if concept_id in blank["group"] and (blank["type"] == "owl:disjointWith" or blank["type"] == "owl:equivalentClass"):
                    self.file.write(" ;\n")

                    # Get the identifier of the other element which is connected to the ellipse
                    if blank["group"].index(concept_id) == 0:
                        complement_id = blank["group"][1]
                    else:
                        complement_id = blank["group"][0]
                    
                    if complement_id is None:
                        # This should not happen
                        continue
                    
                    # Is the other element a named class?
                    if complement_id in concepts:
                        complement_concept = concepts[complement_id]
                        complement_prefix = base_directive_prefix(complement_concept["prefix"])
                        self.file.write(f'\t{blank["type"]} {complement_prefix}{complement_concept["uri"]}')

                    # Is the other element an enumerated class? (i.e. owl:oneOf)
                    elif complement_id in hexagons:
                        complement = hexagons[complement_id]
                        self.file.write("\t" + blank["type"] + " [ rdf:type owl:Class ;")
                        text =  one_of(complement, individuals, diagram_model)
                        self.file.write(text)
                        self.file.write("\t\t]")

                    # Is the other element an union or an intersection of classes? (i.e. owl:intersectionOf or owl:unionOf)
                    elif complement_id in anonymous_concepts:
                        complement = anonymous_concepts[complement_id]

                        # Is the other element an intersection of classes?
                        if complement["type"] == "owl:intersectionOf":
                            self.file.write(f'\t{blank["type"]} [ rdf:type owl:Class ;')
                            text = intersection_of(complement, concepts, diagram_model, hexagons, anonymous_concepts, individuals, all_relations, anonymous_classes, [])
                            self.file.write(text)
                            self.file.write("\t\t]")

                        # Is the other element an union of classes?
                        elif complement["type"] == "owl:unionOf":
                            self.file.write(f'\t{blank["type"]} [ rdf:type owl:Class ;')
                            text = union_of(complement, concepts, diagram_model, hexagons, anonymous_concepts, individuals, all_relations, anonymous_classes, [])
                            self.file.write(text)
                            self.file.write("\t\t]")

                    #owl:disjointWith restriction or owl:complementOf
                    # Is the other element a restriction of a complement class? (i.e. restriction or owl:complementOf)
                    elif complement_id in anonymous_classes:
                        # In this case, the other element is a blank node which is the source of another arrow
                        # (we are just interested in those arrows)
                        complement_id = anonymous_classes[complement_id]["relations"]

                        # Is the blank node the source of an arrow?
                        if len(complement_id) > 0:
                            complement = all_relations[complement_id[0]]

                            # Is the object a restriction?
                            if(complement["type"] == "owl:ObjectProperty"):
                                self.file.write(f'\t{blank["type"]} ')
                                text, more_than_two_restrictions = restrictions(complement, concepts, diagram_model, hexagons, anonymous_concepts, individuals, all_relations, anonymous_classes, complement_id[0], [])
                                self.file.write(text)

                                if more_than_two_restrictions:
                                    prefix = base_directive_prefix(complement["prefix"])
                                    diagram_model.generate_warning("More than one restriction has been defined at the same time. This is not an official notation, but we have generated the restriction anyway", complement_id[0], f'{prefix}{complement["uri"]}', "Restrictions")
                            

                            # Is the object a complement class?
                            elif(complement["type"] == "owl:complementOf"):
                                text = complement_of(complement, concepts, diagram_model, hexagons, anonymous_concepts, individuals, all_relations, anonymous_classes, [])

                                if text != "":
                                    self.file.write(f'\t{blank["type"]} [ rdf:type owl:Class ;')
                                    self.file.write(text)
                                    self.file.write("\t\t]")

            self.file.write(" .\n\n")
    
    # This function writes the declaration of the individuals and indicates if they are instances of a class
    def write_instances(self, diagram_model):
        # Get neccesary attributes
        individuals = diagram_model.get_individuals()

        self.file.write("#################################################################\n"
                "#    Instances\n"
                "#################################################################\n\n")

        # Iterate individuals detected in the diagram
        for ind_id, individual in individuals.items():

            prefix = base_directive_prefix(individual["prefix"])
            uri = individual["uri"]
            types = individual["type"]

            # Write individual declaration
            self.file.write("### " + prefix + uri + "\n")
            self.file.write(f'{prefix}{uri} rdf:type owl:NamedIndividual')

            # Write down the classes to which the individual belongs
            for type in types:
                self.file.write(";\n\t\trdf:type " + type)

            self.file.write(" .\n\n")
    
    # This function write triples (subject predicate object) where the subject is an individual
    def write_triplets(self, diagram_model, associations_individuals):
        # Get neccesary attributes
        individuals = diagram_model.get_individuals()
        uri_references = diagram_model.get_uri_references()
        values = diagram_model.get_property_values()
        anonymous_individuals = diagram_model.get_anonymous_individuals()
        arrows = diagram_model.get_arrows()

        # Iterate the individuals which have been detected to be linked to another element (e.g. through an arrow)
        for id, association in associations_individuals.items():
            # Get the subject of the triple (individual name)
            subject = f'{base_directive_prefix(association["individual"]["prefix"])}{association["individual"]["uri"]}'
            # Get the arrows (annotation properties and object properties) whose source is the individual
            relations = association["relations"]
            # Get the arrows (datatype properties) whose source is the individual
            attributes = association["attributes"]

            # Iterate the annotation properties and object properties whose source is the individual
            for relation_id, relation in relations.items():

                # Is the predicate of the triple an annotation property?
                if 'type' in relation and relation['type'] == 'owl:AnnotationProperty':
                    text = write_annotation_triple(relation_id, relation, individuals, uri_references, values, diagram_model)
                    
                    # Is the annotation valid?
                    if text:
                        self.file.write(f'{subject} {text} .')

                else:
                    # The predicate of the triple is an object property (the target must be another individual)
                    predicate = f'{base_directive_prefix(relation["prefix"])}{relation["uri"]}'
                    target_id = relation["target"]
                    
                    # Is the target a named individual?
                    if target_id in individuals:
                        object = f'{base_directive_prefix(individuals[target_id]["prefix"])}{individuals[target_id]["uri"]}'
                        self.file.write(subject + " " + predicate + " " + object + " .\n")
                    
                    # Is the target an anonymous individual?
                    elif target_id in anonymous_individuals:
                        try:
                            object = get_anonymous_individual(anonymous_individuals[target_id], anonymous_individuals, arrows, individuals, values, diagram_model, [target_id])
                            self.file.write(subject + " " + predicate + " " + object + " .\n")
                        except:
                            diagram_model.generate_error("There is an infinite loop in the diagram between anonymous individuals, involving a named individual.", target_id, subject, "Individual")
                            

            # Iterate the datatype properties whose source is the individual
            for attribute_id, attribute in attributes.items():
                # The predicate of the triple is a datatype property (the target must be a data value)
                predicate = f'{base_directive_prefix(attribute["prefix"])}{attribute["uri"]}'
                target_id = attribute["target"]

                object = parse_data_value(values[target_id])
                
                self.file.write(subject + " " + predicate + " " + object + " .\n")
    
    # This function write two general axioms:
    #   1) owl:AllDisjointClasses, which indicates which classes are disjointness. This is indicated through a disjoint ellipse
    #       with at least two arrows.
    #   2) owl:AllDifferent, which indicates that a group of individuals are all different from each other. This is indicated through
    #       an hexagon whose name is owl:AllDifferent.
    def write_general_axioms(self, diagram_model):
        # Get neccesary attributes
        concepts = diagram_model.get_classes()
        anonymous_concepts = diagram_model.get_ellipses()
        individuals = diagram_model.get_individuals()
        hexagons = diagram_model.get_hexagons()
        rhombuses = diagram_model.get_rhombuses()
        anonymous_individuals = diagram_model.get_anonymous_individuals()
        arrows = diagram_model.get_arrows()
        values = diagram_model.get_property_values()

        attribute_blocks = diagram_model.get_datatype_properties()
        relations = diagram_model.get_arrows()

        self.file.write("#################################################################\n"
                "#    General Axioms\n"
                "#################################################################\n\n")

        # Iterate all the ellipses
        for blank_id, blank in anonymous_concepts.items():

            # Is a disjoint ellipse with three or more arrows?
            if len(blank["group"]) > 2 and blank["type"] in ["owl:disjointWith"]:
                self.file.write("[ rdf:type owl:AllDisjointClasses ;\n")
                self.file.write("  owl:members ( \n")

                # Iterate the elements connected to the disjoint ellipse
                for id in blank["group"]:

                    # Is the element a class?
                    if id in concepts:
                        # Get the names of the classes which are disjointness
                        name = f'{base_directive_prefix(concepts[id]["prefix"])}{concepts[id]["uri"]}'
                        self.file.write("\t\t" + name + "\n")

                    else:
                        diagram_model.generate_error("An element of an owl:disjointWith axiom is not a class", id, None, "Ellipses")

                self.file.write("\t\t)")
                self.file.write("] .")

        # Iterate all the hexagons
        for hex_id, hexagon in hexagons.items():

            # Does the hexagon have a name called "owl:AllDifferent"?
            if hexagon["type"] == "owl:AllDifferent":
                self.file.write("[ rdf:type owl:AllDifferent ;\n")
                self.file.write("  owl:distinctMembers ( \n")

                # Iterate the elements connected to the owl:AllDifferent hexagon
                for id in hexagon["group"]:

                    # Is the element a named individual?
                    if id in individuals:
                        # Get the names of the individuals which are disjointness
                        name = f'{base_directive_prefix(individuals[id]["prefix"])}{individuals[id]["uri"]}'
                        self.file.write("\t\t" + name + "\n")
                    
                    # Is the element an anonymous individual?
                    elif id in anonymous_individuals:
                        try:
                            object = get_anonymous_individual(anonymous_individuals[id], anonymous_individuals, arrows, individuals, values, diagram_model, [id])
                            self.file.write("\t\t" + object + "\n")
                        except:
                            diagram_model.generate_error("There is an infinite loop in the diagram between anonymous individuals, involving an owl:AllDifferent hexagon.", id, None, "Individual")

                    else:
                        diagram_model.generate_error("An element of an owl:AllDifferent axiom is not an individual", id, None, "Hexagons")

                self.file.write("\t\t)")
                self.file.write("] .")

            # Does the hexagon have a name called "owl:AllDisjointProperties"?  
            elif hexagon["type"] == "owl:AllDisjointProperties":

                if len(hexagon["group"]) > 2:
                    self.file.write("[ rdf:type owl:AllDisjointProperties ;\n")
                    self.file.write("  owl:members ( \n")

                    # List to store the names of the rhombhuses involved in the axiom
                    name = []
                    # Variable to store the number of rhombhuses that have been identified as datatype properties
                    count_dp = 0
                    # Variable to store the number of rhombhuses that have been identified as object properties
                    count_op = 0

                    # Iterate the elements connected to the owl:AllDisjointProperties hexagon
                    for id in hexagon["group"]:

                        # Is the element an individual?
                        if id in rhombuses:

                            # Has the rhombus been identified as a datatype property?
                            if id in attribute_blocks:
                                count_dp += 1
                            
                            # Has the rhombus been identified as an object property?
                            elif id in relations and relations[id]['type'] == 'owl:ObjectProperty':
                                count_op += 1
                            
                            else:
                                diagram_model.generate_error("An element of an owl:AllDisjointProperties axiom is not an object or datatype property", id, f'{base_directive_prefix(rhombuses[id]["prefix"])}{rhombuses[id]["uri"]}', "Hexagons")
                                continue

                            # Get the names of the individuals which are disjointness
                            name.append(f'\t\t{base_directive_prefix(rhombuses[id]["prefix"])}{rhombuses[id]["uri"]}\n')

                        else:
                            diagram_model.generate_error("An element of an owl:AllDisjointProperties axiom is not a rhombus", id, None, "Hexagons")

                    # Are there object and datatype properties at the same time?
                    if count_dp != 0 and count_op != 0:
                        diagram_model.generate_error("There are datatype and object properties involved in an owl:AllDisjointProperties axiom at the same time", id, None, "Hexagons")

                    else:
                        self.file.writelines(name)

                    self.file.write("\t\t)")
                    self.file.write("] .")
                
                else:
                    diagram_model.generate_error("At least three properties must be involved in an owl:AllDisjointProperties axiom. If only two properties are involved, owl:propertyDisjointWith should be used", hex_id, None, "Hexagons")
            
# For each prefix that it is used but is not declared in the namespaces,
# create that prefix with a default uri
def create_prefix_not_declared(prefixes_identified, namespaces):
    not_found = []
    for prefix in prefixes_identified:
        if prefix not in namespaces:
            not_found.append(prefix)

    default_uri = "http://www.owl-ontologies.com/{}#"
    new_namespaces = dict()

    for ns in not_found:
        if(ns != "" and ns != ':'):
            new_namespaces[ns] = default_uri.format(ns)

    return new_namespaces

# Check if the user has defined "@base" and the empty prefix ':'
# Prepare the "@prefix prefix:uri ." for each prefix
def find_base_and_empty_prefix(namespaces, diagram_model):
    base_uri, base_prefix, empty_prefix = '', '', ''
    prefixes = []

    for prefix, uri in namespaces.items():
        if (prefix == "@base"):
            base_uri = uri
            base_prefix = prefix

        else:
            if prefix != 'xml' and check_valid_prefix(uri):
                diagram_model.generate_error("A namespace has to finish with / or #. A # has been added at the end of the namespace", None, f'{prefix}: {uri}', "Namespaces")
                uri += '#'

            if(prefix == ""):
                empty_prefix = uri

            else:
                prefixes.append("@prefix " + prefix + ": <" + uri + "> .\n")

    return prefixes, base_uri, base_prefix, empty_prefix

# If the user has not declared "@base" in the namespaces. The base prefix is:
    # 1) The first prefix defined by the user in the namespaces
    # 2) The first prefix that is not defined in the namespaces, but it is used as a prefix in an element
    # 3) Default chowlk base
def select_base(namespaces, new_namespaces):
    if len(namespaces) == 9:
        if new_namespaces:
            base_prefix = list(new_namespaces.keys())[0]
            base_uri = new_namespaces[base_prefix]
        else:
            base_prefix = 'chowlk'
            base_uri = 'http://www.owl-ontologies.com/chowlk#'
    else:
        base_prefix = list(namespaces.keys())[0]
        base_uri = namespaces[base_prefix]

    return base_prefix, base_uri

# Check if a prefix finish with '/' or '#'
def check_valid_prefix(prefix):
    return prefix[-1] != '/' and prefix[-1] != '#'

# Check if an element of a triple is an uri
def check_is_uri(uri):
    return uri[0] == '<' and uri[-1] == '>'

