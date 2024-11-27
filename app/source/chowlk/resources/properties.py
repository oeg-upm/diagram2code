from app.source.chowlk.resources.anonymousClass import *
from app.source.chowlk.resources.utils import base_directive_prefix

# This function obtain the triples (subject predicate object) where:
# - subject is a property (datatype or object property)
# - predicate is either rdfs:domain or rdfs:range
# - object is a class description
def properties_domain_range(relation_id, property_prefix, property_uri, object, range_domain, property, domain_range, concepts, hexagons, diagram_model, individuals, anonymous_concepts, anonymous_classes, relations, attribute_blocks, anonymous_individuals):
    predicate = ":"

    # Is the object a box which is under a class?
    if object in attribute_blocks:
        predicate = obtained_named_class_through_datatype_property(attribute_blocks, concepts, object, anonymous_classes, diagram_model)

    # Is the object a class?
    elif object in concepts:
        predicate = obtain_named_class(concepts, object)

    # Is the object an enumerated class?
    elif object in hexagons:
        predicate = obtain_enumerated_class(hexagons, object, individuals, diagram_model, domain_range, relation_id, property_prefix, property_uri, property) 

    # Is the object an union or intersection of class descriptions?
    elif object in anonymous_concepts:
        predicate = obtain_union_intersection_of_classes(anonymous_concepts, object, concepts, diagram_model, hexagons, individuals, relations, anonymous_classes, domain_range, relation_id, property_prefix, property_uri, property)

    # Is the object a restriction or a complement class description?
    elif object in anonymous_classes:
        predicate = obtain_complement_restriction_of_classes(anonymous_classes, object, relations, relation_id, concepts, diagram_model, hexagons, anonymous_concepts, individuals)

    # Is the object a named or an anonymous individual?
    elif object in individuals or object in anonymous_individuals:
        
        # Does the arrow connect two element which represents individuals?
        if property == 'object property' and range_domain not in individuals and range_domain not in anonymous_individuals:
            # In this case there is an object property which connects a named or anonymous individual to an element which does not represent an individual
            diagram_model.generate_error("The " + domain_range + " of an " + property + " is an individual", relation_id, f'{property_prefix}{property_uri}', "Relations")
        
    else:
        diagram_model.generate_error("The " + domain_range + " of an " + property + " is not a class description", relation_id, f'{property_prefix}{property_uri}', "Relations")

    return predicate

# This function obtained :
# 1) the name of a named class that is associated to the datatype property to which the arrow is connected (i.e. the concept associated to the attribute).
# 2) the datatype restriction that is associated to the datatype property to which the arrow is connected (i.e. the concept associated to the attribute).
def obtained_named_class_through_datatype_property(attribute_blocks, concepts, object, anonymous_classes, diagram_model):
    predicate = ':'
    # Get the identifier of the class associated to the datatype property
    concept_id = attribute_blocks[object]["concept_associated"]

    # Is it really a named class? 
    if concept_id in concepts:
        concept = concepts[concept_id]
        prefix = base_directive_prefix(concept["prefix"])
        predicate = prefix + concept["uri"]

    # Does the block represent a blank node?
    elif concept_id in anonymous_classes:
        # In this case "object" is the identifier of a datatype property block which is below the blank node
        # Get the first datatype property of the datatype property block which is below the blank node
        datatype_property = attribute_blocks[object]["attributes"][0]
        predicate = datatype_property_restriction(datatype_property, diagram_model, object)[0]
    
    #else:
        # The box which is on top of the attribute has not been identified as a concept.
        # This error is derived from another error (the box above the attribute has another error),
        # for that reason, an exception is not raise here (to avoid duplication)

    return predicate

# This function obtain the name of a named class.
def obtain_named_class(concepts, object):
    concept = concepts[object]
    prefix = base_directive_prefix(concept["prefix"])

    return prefix + concept["uri"]

# This function obtain the declaration of a class description which represents an enumeration of individuals.
# An enumeration of individuals is represented through an hexagon whose name is owl:oneOf, which has to be connected
# to individuals.
def obtain_enumerated_class(hexagons, object, individuals, diagram_model, domain_range, relation_id, property_prefix, property_uri, property):
    predicate = ":"
    # Get the hexagon
    hexagon = hexagons[object]

    # Does the hexagon represent an owl:oneOf?
    if hexagon["type"] == "owl:oneOf":
        predicate = "[ rdf:type owl:Class ;"
        predicate = predicate +  one_of(hexagon, individuals, diagram_model) 
        predicate = predicate + "\t\t]" 

    else:
        diagram_model.generate_error("The " + domain_range + " of an " + property + " is not a class description", relation_id, f'{property_prefix}{property_uri}', "Relations")

    return predicate

# This function obtain the declaration of a class description which represents an intersection or an union
# of class descriptions. An intersection or an union is represented through an ellipse, which has to be connected
# to class descriptions.
def obtain_union_intersection_of_classes(anonymous_concepts, object, concepts, diagram_model, hexagons, individuals, relations, anonymous_classes, domain_range, relation_id, property_prefix, property_uri, property):
    predicate = ":"
    # Get the ellipse
    ellipse = anonymous_concepts[object]

    # Does the ellipse represent an owl:intersectionOf?
    if ellipse["type"] == "owl:intersectionOf":
        predicate = "[ rdf:type owl:Class ;"
        predicate = predicate + intersection_of(ellipse, concepts, diagram_model, hexagons, anonymous_concepts, individuals, relations, anonymous_classes, [])
        if predicate == "":
            #empty domain
            predicate = ":"
        else:
            predicate = predicate + "\t\t]"

    # Does the ellipse represent an owl:unionOf?
    elif ellipse["type"] == "owl:unionOf":
        predicate = "[ rdf:type owl:Class ;"
        predicate = predicate + union_of(ellipse, concepts, diagram_model, hexagons, anonymous_concepts, individuals, relations, anonymous_classes, [])
        if predicate == "":
            #empty domain
            predicate = ":"
        else:
            predicate = predicate + "\t\t]"
    else:
        diagram_model.generate_error("The " + domain_range + " of an " + property + " is not a class description", relation_id, f'{property_prefix}{property_uri}', "Relations")

    return predicate

# This function obtain the declaration of a class description which represents a complement of a class or a 
# restriction. Both are represented as a blank node which is the source of an arrow. If the arrow name is not
# owl:complementOf that means that the user is defining a restriction. Otherwise is a complement.
def obtain_complement_restriction_of_classes(anonymous_classes, object, relations, relation_id, concepts, diagram_model, hexagons, anonymous_concepts, individuals):
    predicate = ":"

    # Is there at least one datatype property block below the blank node?
    if anonymous_classes[object]['attributes']:
        datatype_properties = diagram_model.get_datatype_properties()
        # Get the identifier of the first datatype property block which is below the blank node
        d_p_block_id = anonymous_classes[object]["attributes"][0]
        # Get the first datatype property of the first datatype property block which is below the blank node
        datatype_property = datatype_properties[d_p_block_id]['attributes'][0]
        predicate = datatype_property_restriction(datatype_property, diagram_model, d_p_block_id)[0]
    
    else:
        # Get the arrows whose source is the blank node
        arrows = anonymous_classes[object]["relations"]
        if len(arrows) > 0:
            #Well, there is the possibility that the same object property is detected as
            #the relation whose source is the complement. For that reason, it is neccesary to skip
            #the object property
            if arrows[0] != relation_id:
                arrow = relations[arrows[0]]
                arrow_id = arrows[0]
            elif len(arrows) > 1:
                arrow = relations[arrows[1]]
                arrow_id = arrows[1]
            else:
                return ":"

            if(arrow["type"] == "owl:ObjectProperty"):
                predicate = restrictions(arrow, concepts, diagram_model, hexagons, anonymous_concepts, individuals, relations, anonymous_classes, arrow_id, [])[0]
                if predicate == "":
                    #empty domain
                    predicate = ":"

            elif(arrow["type"] == "owl:complementOf"):
                predicate = complement_of(arrow, concepts, diagram_model, hexagons, anonymous_concepts, individuals, relations, anonymous_classes, [])
                if predicate == "":
                    #empty domain
                    predicate = ":"
                else:
                    predicate = "[ rdf:type owl:Class ;" + predicate + "\t\t]"

    return predicate

# Function to obtain the properties which are part of a property chain axiom. A property chain axiom is defined
# through a collection where the order matters
def obtain_elements_property_chain(diagram_model, relations, relation_id):
    text = ""
    # Check if really the element is an object property
    if relation_id in relations:
        # Get the object property
        relation = relations[relation_id]
        # Get the object property name
        text = f" {base_directive_prefix(relation['prefix'])}{relation['uri']} "

        # Check if the end of path that defines the property chain axiom has been reached
        if "aggregation" in relation:
            
            # Just one path can be defined, so the array should contains just one element
            if len(relation["aggregation"]) > 1:
                # Just one path can be defined in a property chain axiom
                diagram_model.generate_error("Just one path can be defined in a property chain axiom", relation_id, text, "Rhombuses")

            # Go to the next element
            text += obtain_elements_property_chain(diagram_model, relations, relation["aggregation"][0][0])
    
    return text
