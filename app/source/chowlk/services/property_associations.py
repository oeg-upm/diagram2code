from app.source.chowlk.resources.utils import base_directive_prefix
import copy

# This function add the relations betweem properties.
def enrich_properties(diagram_model):

    rhombuses = diagram_model.get_rhombuses()
    relations = diagram_model.get_arrows()
    datatype_properties = diagram_model.get_datatype_properties()
    concepts = diagram_model.get_classes()
    hexagons = diagram_model.get_hexagons()
    
    relations_copy = enrich_properties_through_relations(diagram_model, relations, rhombuses, datatype_properties, concepts, hexagons, copy.deepcopy(relations))
    check_rhombus_names(rhombuses, relations_copy, diagram_model)
    
    diagram_model.set_arrows(relations_copy)
    check_property_aggregations(diagram_model)

# Function to check if all the aggregations between properties are part of a path of a property chain
def check_property_aggregations(diagram_model):
    aggregations = []
    propertyChain = []
    arrows = diagram_model.get_arrows()

    for arrow_id, arrow in arrows.items():
        arrow_type = arrow['type'] if 'type' in arrow else None
        target_id = arrow['target'] if 'target' in arrow else None
        source_id = arrow['source'] if 'source' in arrow else None
        if arrow_type == 'aggregation' and target_id in arrows and source_id in arrows:
            aggregations.append(arrow_id)
        elif arrow_type == 'owl:propertyChainAxiom':

            if target_id in arrows:
                aux(arrows[target_id], propertyChain, arrows)
    
    for aggregation in aggregations:

        if aggregation not in propertyChain:
            diagram_model.generate_error(f'A path used to describe a property chain is not part of a correct property chain axiom. It lacks the owl:propertyChainAxiom arrow', aggregation, None, "Rhombuses")

def aux(target, propertyChain, arrows):
    if "aggregation" in target:

        for aggregation in target["aggregation"]:

            if aggregation[1] not in propertyChain:
                propertyChain.append(aggregation[1])
            
            if aggregation[0] in arrows:
                aux(arrows[aggregation[0]], propertyChain, arrows)

# The objective of this function is to find the relations between properties (e.g. rdfs:subPropertyOf) in order to
# add that information into the properties (i.e. relations or attribute_blocks).
# The source and target of the relations beetween properties must be rhombuses (because properties are represented in rhombuses).
# Moreover this function also find the domain and range of properties that are declared through rhombuses.
# Moreover this function also find the annotation properties of properties that are declared as rhombuses.
def enrich_properties_through_relations(diagram_model, relations, rhombuses, attribute_blocks, concepts, hexagons, relations_copy):

    # Name of allowed relations between properties, properties domain/range and annotation properties
    cases = ["rdfs:subPropertyOf", "owl:inverseOf",
                 "owl:equivalentProperty", "rdfs:domain", "rdfs:range", "owl:propertyDisjointWith", "owl:AnnotationProperty",
                 "owl:propertyChainAxiom", "aggregation"]
    
    # Iterate all the arrows
    for arrow_id, arrow in relations.items():
        # Get the source and target of the arrow
        source_id = arrow["source"]
        target_id = arrow["target"]

        # Has the relation a source and a target defined?
        if source_id is None or target_id is None:
            continue

        # Get the type of the arrow
        relation_type = arrow["type"] if "type" in arrow else None
        
        # Is the arrow defining a relation between properties?
        if relation_type in cases:
            # If the type is rdfs:domain or rdfs:range, just take the part after the ':' because the domain and range
            # are stored in the data structure as "domain" or "range" respectively
            relation_type = relation_type.split(":")[1] if relation_type in ["rdfs:domain", "rdfs:range"] else relation_type

            # Is a relation between properties? (i.e. the source and target of the relation are rhombuses)
            if source_id in rhombuses and target_id in rhombuses:
                # Get the source rhombus
                source_property = rhombuses[source_id]

                # Is the relation between properties valid?
                if relation_type != 'domain' and relation_type != 'range':
                    # In this case the relation is added to the rhombus that has been defined as the source of the relation
                    target_property = rhombuses[target_id]

                    # Are not property types the same? (e.g. one rhombus is representing a dataype property and the other
                    # and object property)
                    if source_property['type'] != target_property['type']:
                        value = f'{base_directive_prefix(source_property["prefix"])}{source_property["uri"]}'
                        diagram_model.generate_error(f'A {relation_type} relation can not been defined between different types of properties', source_id, value, "Rhombuses")

                    # Is an invalid property? (i.e. the user is trying to define an owl:inverseOf relation between datatype properties)
                    elif relation_type == 'owl:inverseOf' and source_property['type'] == 'owl:DatatypeProperty':
                        value = f'{base_directive_prefix(source_property["prefix"])}{source_property["uri"]}'
                        diagram_model.generate_error('A owl:inverseOf relation can not been defined between datatype properties', source_id, value, "Rhombuses")
                    
                    else:
                        # sprop_type stores the type of the property which is the subject of the triple (i.e. object or datatype property)
                        sprop_type = source_property["type"]     
                        # Get the name of the target property
                        target_property_name = f'{base_directive_prefix(target_property["prefix"])}{target_property["uri"]}' 

                        # Has the source rhombus been defined as an object property?
                        if sprop_type == "owl:ObjectProperty":

                            if relation_type == "owl:propertyChainAxiom":
                                # Store the id of the target property
                                add_object_property_triple(relation_type, relations_copy, source_id, target_id)
                            
                            elif relation_type == "aggregation":
                                # Store the id of the target property and the id of the arrow
                                add_object_property_triple(relation_type, relations_copy, source_id, [target_id, arrow_id])
                            
                            else:
                                # Store the name of the target property
                                add_object_property_triple(relation_type, relations_copy, source_id, target_property_name)

                        # Has the source rhombus been defined as a datatype property?
                        elif sprop_type == "owl:DatatypeProperty":
                            # A owl:propertyChainAxiom and aggregation can not be defined between datatype properties
                            if relation_type == "owl:propertyChainAxiom" or relation_type == "aggregation":
                                value = f'{base_directive_prefix(source_property["prefix"])}{source_property["uri"]}'
                                diagram_model.generate_error("A property chain can not been defined between datatype properties", source_id, value, "Rhombuses")
                            else:
                                # Add the relation to the corresponding datatype property.
                                # Remember that in a rhombus just one datatype property can be defined 
                                # (i.e. the array always have just one element).
                                # attribute_blocks[source_id]["attributes"][0][relation_type] = target_property_name
                                add_datatype_property_triple(relation_type, attribute_blocks, source_id, target_property_name)

                else:
                    value = f'{base_directive_prefix(source_property["prefix"])}{source_property["uri"]}'
                    diagram_model.generate_error(f'A {relation_type} relation can not been defined between rhombuses', source_id, value, "Rhombuses")
            
            # Is a domain or range declaration?
            elif source_id in rhombuses and relation_type in ["domain", "range"]:

                source_property = rhombuses[source_id]
                # sprop_type stores the type of the property which is the subject of the triple (i.e. object or datatype property)
                sprop_type = source_property["type"]

                # Has the source rhombus been defined as an object property?
                if sprop_type == "owl:ObjectProperty":
                    # Add domain/range
                    # This has to be modified to allow multiple declaration of domain and ranges in rhombuses
                    relations_copy[source_id][relation_type] = target_id

                # Has the source rhombus been defined as a datatype property?
                elif sprop_type == "owl:DatatypeProperty":

                    # Is the relation a rdfs:range?
                    if relation_type == "range":
                        
                        # Is the target a datatype? (i.e. the target has been identified as a concept)
                        if target_id in concepts:
                            # In this case, the dataype has been identified incorrectly as a concept.
                            # The datatype information is retreived from the concept.
                            # Moreover, it is neccesary to remove that concept (because it is not really a concept)
                            attribute_blocks[source_id]["attributes"][0][relation_type] = True
                            incorrect_concept = concepts.pop(target_id)
                            prefix_datatype = incorrect_concept["prefix"]
                            datatype = incorrect_concept["uri"]

                            # If there is not a prefix, the default prefix for a datatype is xsd (not the base)
                            if not prefix_datatype and datatype.startswith('<#'):
                                prefix_datatype = "xsd"
                                datatype = datatype[2:-1]

                            attribute_blocks[source_id]["attributes"][0]["datatype"] = datatype
                            attribute_blocks[source_id]["attributes"][0]["prefix_datatype"] = prefix_datatype

                        # Is the range an enumerated datatype? (i.e. the target is an hexagon)
                        elif target_id in hexagons:
                            attribute_blocks[source_id]["attributes"][0]['range'] = target_id

                        else:
                            value = f'{base_directive_prefix(attribute_blocks[source_id]["attributes"][0]["prefix"])}{attribute_blocks[source_id]["attributes"][0]["uri"]}'
                            diagram_model.generate_error("The range of a datatype property is not a datatype or an enumerated datatype", source_id, value, "Attributes")

                    else:
                        # The relation is a rdfs:domain
                        attribute_blocks[source_id]["attributes"][0][relation_type] = target_id

            # Is an annotation property triple?
            elif source_id in rhombuses and relation_type == 'owl:AnnotationProperty':
                source_property = rhombuses[source_id]
                sprop_type = source_property["type"]

                # Has the source rhombus been defined as an object property?
                if sprop_type == 'owl:ObjectProperty':
                    # Store the annotation relation identifier
                    add_object_property_triple('annotation', relations_copy, source_id, arrow_id)
                
                # Has the source rhombus been defined as a datatype property?
                elif sprop_type == "owl:DatatypeProperty":

                    if 'annotation' in attribute_blocks[source_id]["attributes"][0]:
                        attribute_blocks[source_id]["attributes"][0]['annotation'].append(arrow_id)
                    else:
                        attribute_blocks[source_id]["attributes"][0]['annotation'] = [arrow_id]
            
            elif source_id in rhombuses or target_id in rhombuses:
                diagram_model.generate_error(f'A {relation_type} relation just can be defined between rhombuses', source_id, None, "Rhombuses")

        # Is the arrow defining a non-valid relation between properties?
        elif source_id in rhombuses and target_id in rhombuses:
            source_property = rhombuses[source_id]
            value = f'{base_directive_prefix(source_property["prefix"])}{source_property["uri"]}'
            diagram_model.generate_error(f'A {relation_type} relation can not been defined between rhombuses', source_id, value, "Rhombuses")
                    
    return relations_copy

# This function add the relation (predicate) between objects properties to the object property which is the subject of the triple.
# The same object property can be the subject of more than one triples with the same predicate (predicate), for example a property 
# can be the subject of more than one rdfs:subPropertyOf statement. For that reason, an array is created to store the objects (another
# object property) for each predicate (predicate).
# Moreover, this function add the domain and ranges of properties (with the same reasoning explained above).
def add_object_property_triple(predicate, relations_copy, source_id, object):

    # Is there another object defined for that predicate?
    if predicate in relations_copy[source_id]:
        relations_copy[source_id][predicate].append(object)

    else:
        # Create an array in order to store the objects for that predicate.
        relations_copy[source_id][predicate] = [object]

def add_datatype_property_triple(predicate, attribute_blocks, source_id, object):

    datatype_property = attribute_blocks[source_id]["attributes"][0]

    # Is there another object defined for that predicate?
    if predicate in datatype_property:
        datatype_property[predicate].append(object)
    
    else:
        # Create an array in order to store the objects for that predicate.
        datatype_property[predicate] = [object]

# This function check for its rhombus if the property has been used incorrectly in another element. Specifically:
#   - Check if a datatype property which has been declared through a rhombus has been used in an arrow as an object property.
#   - Check if an object property which has been declared through a rhombus has been used in an arrow as a datatype property.
def check_rhombus_names(rhombuses, relations_copy, diagram_model):
    relations_byname = {f'{base_directive_prefix(relation["prefix"])}{relation["uri"]}': id for id,
                    relation in relations_copy.items() if "uri" in relation}
    
    # Iterate all the rhombus
    for rhombus_id, rhombus in rhombuses.items():

        type = rhombus["type"]
        prop_name = f'{base_directive_prefix(rhombus["prefix"])}{rhombus["uri"]}'

        # Is the rhombus a datatype property?
        if type == "owl:DatatypeProperty":

            # Has the datatype property been used in an arrow?
            if prop_name in relations_byname:
                # Get the identifier of the arrow
                prop_id = relations_byname[prop_name]

                # Is the arrow used as an object property?
                if relations_copy[prop_id]["type"] == "owl:ObjectProperty":
                    diagram_model.generate_error("A rhombus can not be defined as Object Property and Datatype Property at the same time", rhombus_id, prop_name, "Rhombuses")

        # Is the rhombus an object property?
        elif type == "owl:ObjectProperty":

            # Has the object property been used in an arrow?
            if prop_name in relations_byname:
                # Get the identifier of the arrow
                prop_id = relations_byname[prop_name]

                # Is the arrow used as a datatype property?
                if relations_copy[prop_id]["type"] == "owl:DatatypeProperty":
                    diagram_model.generate_error("A rhombus can not be defined as Object Property and Datatype Property at the same time", rhombus_id, prop_name, "Rhombuses")
