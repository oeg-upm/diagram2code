from source.chowlk.geometry import get_corners, get_corners_rect_child
import copy

def resolve_concept_reference(attribute_blocks, concepts):
    """
    This function resolves the relative references that attribute blocks could have.
    This occur when a concept have two blocks of attributes attacked to it, i.e.
    one with domain and the other without domain. The last block have as associated concept
    the attribute block on top of it instead of the concept itself.

    :arg attribute_blocks: list of attribute blocks.
    :arg concepts: list of concepts.
    :return list of attributes with the correct associated concepts.
    """

    for id, attribute_block in attribute_blocks.items():
        if "concept_associated" not in attribute_block:
            continue
        source_id = attribute_block["concept_associated"]
        # Check if the object associated to this set of attributes (attribute block) is really a concept
        if source_id not in concepts and source_id in attribute_blocks:
            # If a the id was not from a concept look for the attributes associated
            # and take its concept associated
            real_id = attribute_blocks[source_id]["concept_associated"]
            attribute_blocks[id]["concept_associated"] = real_id

            for attribute in attribute_block["attributes"]:
                if attribute["domain"] != False:
                    attribute["domain"] = real_id

    return attribute_blocks


def concept_attribute_association(concepts, attribute_blocks):

    associations = {}

    for id, concept in concepts.items():
        associations[id] = {"concept": concept, "attribute_blocks": {}, "relations": {}}

    for id, attribute_block in attribute_blocks.items():
        if "concept_associated" in attribute_block:
            concept_id = attribute_block["concept_associated"]
            if concept_id in associations:
                associations[concept_id]["attribute_blocks"][id] = attribute_block

    return associations


def concept_relation_association(associations, relations):

    for relation_id, relation in relations.items():
        type = relation["type"] if "type" in relation else None
        if type in ["rdf:type", "ellipse_connection", "rdfs:range", "rdfs:domain"]:
            continue
        source_id = relation["source"]
        target_id = relation["target"]

        if source_id is None or target_id is None:
            continue

        for s_concept_id, association in associations.items():
            if source_id == s_concept_id or source_id in association["attribute_blocks"]:
                associations[s_concept_id]["relations"][relation_id] = relation
                relations[relation_id]["source"] = s_concept_id

                for t_concept_id, association in associations.items():
                    if target_id == t_concept_id or target_id in association["attribute_blocks"]:
                        associations[s_concept_id]["relations"][relation_id]["target"] = t_concept_id
                        relations[relation_id]["target"] = t_concept_id
                        break

    return associations, relations


def individual_type_identification(individuals, associations, relations):

    for id, relation in relations.items():

        if "type" not in relation:
            continue

        if relation["type"] != "rdf:type":
            continue
        source_id = relation["source"]
        target_id = relation["target"]
        
        if source_id is None or target_id is None:
            continue

        try:
            individual = individuals[source_id]
            individual["type"] = []
        except:
            continue

        for concept_id, association in associations.items():

            if target_id == concept_id or target_id in association["attribute_blocks"]:

                prefix = association["concept"]["prefix"]
                uri = association["concept"]["uri"]
                individual["type"].append(prefix + ":" + uri)

    for ind_id, individual in individuals.items():
        try:
            geometry = individual["xml_object"][0]
            x, y = float(geometry.attrib["x"]), float(geometry.attrib["y"])
            width, height = float(geometry.attrib["width"]), float(geometry.attrib["height"])
            p1, p2, p3, p4 = get_corners(x, y, width, height)

            for concept_id, association in associations.items():
                concept = association["concept"]
                geometry = concept["xml_object"][0]
                x, y = float(geometry.attrib["x"]), float(geometry.attrib["y"])
                width, height = float(geometry.attrib["width"]), float(geometry.attrib["height"])
                p1_support, p2_support, p3_support, p4_support = get_corners(x, y, width, height)
                dx = abs(p1[0] - p2_support[0])
                dy = abs(p1[1] - p2_support[1])
                if dx < 5 and dy < 5:
                    individual["type"].append(concept["prefix"] + ":" + concept["uri"])
                    break
        except:
            continue

    return individuals




def enrich_properties(rhombuses, relations, attribute_blocks, concepts):

    relations_byname = {relation["uri"]: id for id, relation in relations.items() if "uri" in relation}
    attributes_byname = {attribute["uri"]: [id, idx] for id, attribute_block in attribute_blocks.items()
                         for idx, attribute in enumerate(attribute_block["attributes"])}
    relations_copy = copy.deepcopy(relations)
    for relation_id, relation in relations.items():

        source_id = relation["source"]
        target_id = relation["target"]
        
        if source_id is None or target_id is None:
            continue

        type = relation["type"] if "type" in relation else None
        cases = ["rdfs:subPropertyOf", "owl:inverseOf", "owl:equivalentProperty", "rdfs:domain", "rdfs:range"]

        if type in cases:
            # Domain and range are without the "rdfs" prefix in the data structure
            type = type.split(":")[1] if type in ["rdfs:domain", "rdfs:range"] else type

            if source_id in rhombuses and target_id in rhombuses:

                source_property = rhombuses[source_id]
                target_property = rhombuses[target_id]
                sprop_type = source_property["type"]
                sprop_name = source_property["uri"]

                if sprop_type == "owl:ObjectProperty":
                    sprop_id = relations_byname[sprop_name]
                    relations_copy[sprop_id][type] = target_property["prefix"] + ":" + target_property["uri"]

                elif sprop_type == "owl:DatatypeProperty":
                    sprop_id = attributes_byname[sprop_name][0]
                    sprop_idx = attributes_byname[sprop_name][1]
                    attribute_blocks[sprop_id]["attributes"][sprop_idx][type] = target_property["prefix"] + ":" + target_property["uri"]

            elif source_id in rhombuses and type in ["domain", "range"]:

                source_property = rhombuses[source_id]
                sprop_type = source_property["type"]
                sprop_name = source_property["uri"]

                if sprop_type == "owl:ObjectProperty":
                    sprop_id = relations_byname[sprop_name]
                    relations_copy[sprop_id][type] = target_id

                elif sprop_type == "owl:DatatypeProperty":
                    sprop_id = attributes_byname[sprop_name][0]
                    sprop_idx = attributes_byname[sprop_name][1]
                    attribute_blocks[sprop_id]["attributes"][sprop_idx][type] = target_id
                    
                    if type == "range":
                        attribute_blocks[sprop_id]["attributes"][sprop_idx]["datatype"] = concepts[target_id]["prefix"] + ":" + concepts[target_id]["label"]


    for rhombus_id, rhombus in rhombuses.items():

        try:
            type = rhombus["type"]
            prop_name = rhombus["uri"]
            if type == "owl:InverseFunctionalProperty":
                prop_id = relations_byname[prop_name]
                relations_copy[prop_id]["inverse_functional"] = True
            elif type == "owl:TransitiveProperty":
                prop_id = relations_byname[prop_name]
                relations_copy[prop_id]["transitive"] = True
            elif type == "owl:SymmetricProperty":
                prop_id = relations_byname[prop_name]
                relations_copy[prop_id]["symmetric"] = True
            elif type == "owl:FunctionalProperty":
                if prop_name in relations_byname:
                    prop_id = relations_byname[prop_name]
                    relations_copy[prop_id]["functional"] = True
                else:
                    prop_id = attributes_byname[prop_name][0]
                    prop_idx = attributes_byname[prop_name][1]
                    attribute_blocks[prop_id]["attributes"][prop_idx]["functional"] = True
        except:
            continue

    return relations_copy, attribute_blocks




"""Functions for RDF Data"""

def individual_type_identification_rdf(individuals, concepts, relations):

    for id, relation in relations.items():
        if relation["type"] != "rdf:type":
            continue
        source_id = relation["source"]
        target_id = relation["target"]
        individual = individuals[source_id]
        concept = concepts[target_id]
        if len(individual["type"]) != 0:
            individual["type"].append(concept["prefix"] + ":" + concept["uri"])
        else:
            individual["type"] = [concept["prefix"] + ":" + concept["uri"]]
    for ind_id, individual in individuals.items():
        if individual["type"] is None:
            individual["type"] = []
        p1 = get_corners_rect_child(individual["xml_object"])[0]
        for concept_id, concept in concepts.items():
            p2_concept = get_corners_rect_child(concept["xml_object"])[1]
            dx = abs(p1[0] - p2_concept[0])
            dy = abs(p1[1] - p2_concept[1])
            if dx < 5 and dy < 5:
                individual["type"].append(concept["prefix"] + ":" + concept["uri"])
                break
    return individuals



def individual_relation_association(individuals, relations):

    associations = {}

    for id, individual in individuals.items():
        associations[id] = {"individual": individual, "relations": {}, "attributes": {}}
    for relation_id, relation in relations.items():
        if relation["type"] != "owl:ObjectProperty":
            continue
        source_id = relation["source"]
        target_id = relation["target"]
        if target_id in individuals and source_id in associations:
            association = associations[source_id]
            association["relations"][relation_id] = relation
    return associations


def individual_attribute_association(associations, values, relations):
    
    for relation_id, relation in relations.items():
        source_id = relation["source"]
        target_id = relation["target"]
        if target_id in values and source_id in associations:
            relation["type"] = "owl:DatatypeProperty"
            association = associations[source_id]
            association["attributes"][relation_id] = relation
    return associations