import re
from app.source.chowlk.resources.geometry import get_corners_rect_child
from app.source.chowlk.resources.utils import clean_html_tags, clean_uri, create_label, parse_prefix_uri

# these are the types which can be defined inside a rhombus
rhombus_valid_types = ["owl:ObjectProperty", "owl:DatatypeProperty", "owl:FunctionalProperty",
                "owl:SymmetricProperty", "owl:TransitiveProperty", "owl:InverseFunctionalProperty",
                'owl:AnnotationProperty', 'owl:ReflexiveProperty', 'owl:AsymmetricProperty', 
                'owl:IrreflexiveProperty']

# these are special types that can be defined in an arrow
edge_types = ["rdfs:subClassOf", "rdf:type", "owl:equivalentClass", "owl:disjointWith", "owl:complementOf",
                        "rdfs:subPropertyOf", "owl:equivalentProperty", "owl:inverseOf", "rdfs:domain", "rdfs:range",
                        "owl:sameAs", "owl:differentFrom", "owl:propertyDisjointWith", "owl:propertyChainAxiom"]

class Diagram_model():

    def __init__(self):
        # This attribute store the namespaces (i.e. prefix:suffix) which are defined in the diagram
        self.namespaces = {}
        # This attribute store the ontology metadata (e.g. dcterms:creator, etc.) which is defined in the diagram
        self.ontology_metadata = {}
        # This attribute store the arrows (i.e. arrows connecting two elements) which are defined in the diagram
        self.arrows = {}
        # Sometimes an arrow does not have an xml attribute "value", but this does not indicate that the user has not defined a
        # name for that arrow. In some cases another xml element is created in order to store the name of the arrow. The two following
        # attributes contain the arrows which does not have an xml attribute "value" and the xml object which represents the name of the nameless arrow.
        self.arrows_without_value = {}
        self.arrows_parent = {}
        # This attribute store the ellipses which are defined in the diagram (e.g. union, intersection, etc)
        self.ellipses = {}
        # This attribute store the hexagons which are defined in the diagram (e.g. owl:oneOf declarations)
        self.hexagons = {}
        # This attribute store the individuals (i.e. boxes with underlined names) which are defined in the diagram 
        self.individuals = {}
        # This attribute store the rhombuses which are defined in the diagram (e.g. object property, etc.)
        self.rhombuses = {}
        # Thris attribute store the boxes which are defined in the diagram
        self.boxes = {}
        # This attribute store the property values (i.e. xml elements whose name contains "") which are defined in the diagram.
        # Check that it can be the case that in the same xml element an user can define a property value an a different element
        # (e.g. a datatype property with and owl:hasValue statement)
        self.property_values = {}

        # This attribute store the classes defined in the diagram (boxes which are not below another boxes)
        self.classes = {}
        # This attribute store the attributes defined in the diagram (boxes which are below another boxes)
        self.datatype_properties = {}
        # This attribute store the anonymous classes defined in the diagram (boxes without name or blank boxes)
        self.anonymous_classes = {}
        # This attribute store the anonymous individuals defined in the diagram (boxes without name or blank boxes which are the target of an arrow whose source is a named individual)
        self.anonymous_individuals = {}
        # This attribute store for each arrow with the same name the identifier of the xml object it comes from
        self.arrows_name = {}
        # Thris attribute store the uri_references that are the object of an annotation property triple
        self.uri_references = {}
        
        # This attribute stores the categories of possible errors that a user can make.
        self.errors = {
            "Concepts": [],
            "Arrows": [],
            "Ellipses": [],
            "Attributes": [],
            "Namespaces": [],
            "Metadata": [],
            "Rhombuses": [],
            "Individual": [],
            "Hexagons": [],
            "Cardinality-Restrictions": [],
            "intersectionOf": [],
            "oneOf": [],
            "complementOf": [],
            "unionOf": [],
            "Relations": [],
            "equivalentClass": [],
            "Annotation Properties": [],
            "Base": [],
            # Additional errors which are created if neccesary
            # "Syntax" created in transformations.py
            # "Server Error" created in routes.py
        }

        # This attribute stores the categories of possible warnings that a user can make
        self.warnings = {
            "Restrictions": [],
            "Base": [],
            "Ontology": [],
            "Deprecated": [],
        }
        self.ontology_uri = ''
    
    # Getters
    def get_property_values(self):
        return self.property_values
    
    def get_boxes(self):
        return self.boxes
    
    def get_arrows_without_value(self):
        return self.arrows_without_value
    
    def get_arrows_parent(self):
        return self.arrows_parent
    
    def get_ellipses(self):
        return self.ellipses
    
    def get_hexagons(self):
        return self.hexagons
    
    def get_datatype_properties(self):
        return self.datatype_properties
    
    def get_rhombuses(self):
        return self.rhombuses
    
    def get_arrows(self):
        return self.arrows
    
    def get_arrows_name(self):
        return self.arrows_name
    
    def get_classes(self):
        return self.classes
    
    def get_uri_references(self):
        return self.uri_references
    
    def get_individuals(self):
        return self.individuals
    
    def get_metadata(self):
        return self.ontology_metadata
    
    def get_anonymous_classes(self):
        return self.anonymous_classes
    
    def get_anonymous_individuals(self):
        return self.anonymous_individuals
    
    def get_namespaces(self):
        return self.namespaces
    
    def get_ontology_uri(self):
        return self.ontology_uri
    
    def get_errors(self):
        return self.errors

    def get_warnings(self):
        return self.warnings
    
    # Setters
    def set_arrows(self, relations_copy):
        self.arrows = relations_copy
    
    def set_ontology_uri(self, ontology_uri):
        self.ontology_uri = ontology_uri
    
    # This function iterate the objects defined inside the xml diagram in order to classify them
    # in based of this shapes (e.g. arrows, boxes, rhombuses, etc.)
    def classify_elements(self, root):
        
        # Classify each xml object on the basis of its individual information 
        # (i.e. without taking into account the xml objects to which they are connected).
        for child in root:
            style = child.attrib["style"] if "style" in child.attrib else ""
            value = child.attrib["value"] if "value" in child.attrib else ""
            id = child.attrib["id"]

            # Is a namespace element?
            if "shape=note" in style:
                self.add_namespace(id, value)

            # Is a metadata element?
            elif "shape=document" in style:
                self.add_ontology_metadata(id, value)

            # Is an arrow element?
            elif "edge" in child.attrib:
                self.add_arrow(child, id, value, style)

            # Is an ellipse element?
            elif "ellipse" in style:
                self.add_ellipse(child, id, value)

            # Is an hexagon element?
            elif "hexagon" in style:
                self.add_hexagon(child, id, value)

            # Is a bow element with an underlined name? (<u> in html means underlined text)
            elif "value" in child.attrib and ("fontStyle=4" in style or "<u" in value):
                self.add_individual(child, id, value)

            # Is a rhombus element?
            elif "rhombus" in style:
                self.add_rhombus(child, id, value)

            # Is the name of an arrow?
            elif "edgeLabel" in style or "text" in style:
                self.add_arrow_parent(child, value)

            # Is it a box element?
            elif "rounded" in style:
                self.add_box(child, id, value, style)
            
            # Is there a data value defined in the element? (i.e. the element name contains "")
            if "&quot;" in value or "\"" in value:
                self.add_property_value(id, value, child)

    # Function to find the "note" element in which the namespaces are defined.
    # The namespaces are stored into a dictionary called "namespaces" whose key is 
    # the prefix and the value is the uri.
    # A namespace can be defined as "prefix: uri" or "prefix: <uri>".
    # The uri of the namespace has to start with "http"
    def add_namespace(self, id, value): 
        text = clean_html_tags(value)
        namespaces = text.split("|")
        namespaces = [item for item in namespaces if item.strip() != ""]
        for ns in namespaces:
            try:
                ns = ns.strip()
                # Get the prefix
                prefix = ns.split(":")[0].strip()
                # Get the uri
                uri = ns.split("http")[-1].strip()
                uri = "http" + uri

                # If the uri was defined as "<uri>", remove the "<" and ">"
                if uri[-1] == '>':
                    uri = uri[:-1]
                
                self.namespaces[prefix] = uri

            except:
                self.generate_error("Problems in the text of the Namespace", id, value, "Namespaces")
            
    # Function to find the "document" element in which the ontology metadata is defined.
    # Moreover the ontology uri can be defined as "owl:ontology: uri" or "owl:ontology: <uri>".
    # The metadata is stored into a dictionary called "ontology_metadata" whose key is 
    # the annotation property and the value is the uri.
    # An annotation is defined as "prefix:uri: value" or "prefix:uri: <value>"
    def add_ontology_metadata(self, id, value):
        text = clean_html_tags(value)
        annotations = text.split("|")

        for ann in annotations:

            # The structure of an annotation property defined in the metadata elements must be:
            # prefix:suffix: value where:
            # 1) suffix and prefix are separated by an ':'
            # 2) the value is separated by ' :'
            try:
                # Split the annotation into predicate object
                # Is the annotation defined through an URI?
                if ann[0] == '<':
                    ann_uri = True
                    # Is the blank character a No-Break space (unicode U+00a0)?
                    if ": " in ann:
                        ann_predicate, ann_object = ann.split(">: ", 1)
                    else:
                        ann_predicate, ann_object = ann.split(">: ", 1)
                    
                    ann_predicate = ann_predicate + ">"
                
                else:
                    ann_uri = False
                    # Is the blank character a No-Break space (unicode U+00a0)?
                    if ": " in ann:
                        ann_predicate, ann_object = ann.split(": ", 1)
                    else:
                        ann_predicate, ann_object = ann.split(": ", 1)
                
                if ann_uri:
                    # Is the user defining the ontology uri?
                    if ann_predicate == '<http://www.w3.org/2002/07/owl#Ontology>':
                        self.ontology_uri = ann_object

                    # The user is defining ontology metadata
                    # Is the annotation property already defined?
                    elif ann_predicate in self.ontology_metadata:
                        self.ontology_metadata[ann_predicate].append(ann_object)

                    else:
                        self.ontology_metadata[ann_predicate] = [ann_object]
                
                else:
                    # Split the predicate into prefix suffix
                    ann_prefix, ann_suffix = ann_predicate.split(':', 1)

                    # Removes any leading, and trailing whitespaces
                    ann_prefix = ann_prefix.strip()
                    ann_suffix = ann_suffix.strip()
                    ann_object = ann_object.strip()

                    # Is the user defining the ontology uri?
                    if ann_prefix == 'owl' and ann_suffix == 'Ontology':
                        self.ontology_uri = ann_object

                    # The user is defining ontology metadata
                    # Is the annotation property already defined?
                    elif ann_prefix + ":" + ann_suffix in self.ontology_metadata:
                        self.ontology_metadata[ann_prefix + ":" + ann_suffix].append(ann_object)

                    else:
                        self.ontology_metadata[ann_prefix + ":" + ann_suffix] = [ann_object]

            except:
                self.generate_error("Problems in the text of the Metadata", id, ann, "Metadata")

    # Function to find "edge" elements (i.e. arrows).
    # The "edge" are stored into a dictionary called "arrows" whose key is 
    # the xml id of the element and the value is a dictionary called "arrow".
    # An "arrow" dictionary stores:
    # 1) Source of the arrow (the element id from which the arrow departs)
    # 2) Target of the arrow (the element id on which the arrow ends)
    # 3) The xml element
    def add_arrow(self, child, id, value, style):

        try:

            arrow = {}
            source = child.attrib["source"] if "source" in child.attrib else None
            target = child.attrib["target"] if "target" in child.attrib else None

            arrow["source"] = source
            arrow["target"] = target
            arrow["xml_object"] = child

            # Sometimes the value of a relation is not stored in the same xml object as the arrow. There are 3 cases:
            # 1) the value is stored in another xml object which have an attribute called "parent" whose value is the same as the identifier of the arrow
            # 2) The user has not defined a name for that arrow on purpose (the style of the arrow correspond with the "rdfs:subClassOf" arrow or the "rdf:type" arrow)
            # 3) The user has not defined a name for that arrow because they forgot to name (the style of the arrow does not correspond with the "rdfs:subClassOf" arrow or the "rdf:type" arrow
            if value is None or len(value) == 0:
                # The style is neccesary in order to check if the relation is nameless on purpose
                arrow["style"] = style
                # Store the nameless relation in order to check if it has a value associated in another xml element
                self.arrows_without_value[id] = arrow
                return
            
            self.add_value_to_arrow(arrow, value, style, id)

        except:
            value = clean_html_tags(value) if "value" in child.attrib else None
            # This exception should not happen if the diagram is generated in drawio.io.
            # However if a user changes manually the xml file generated by drawio.io, it could lead to this error.
            self.generate_error("Unexpected error in an arrow occurs. Please contact chowlk staff", id, value, "Arrows") 

    # Function to find "ellipse" elements.
    # The ellipses are stored into a dictionary called "ellipses" whose key is 
    # the xml id of the element an the value is a dictionary called "ellipse".
    # An ellipse dictionary stores:
    # 1) The xml object
    # 2) The type of the ellipse, i.e. what the ellipse represents (e.g. owl:intersectionOf, etc.)
    # 3) The elements id that are related to the ellipse through an arrow
    def add_ellipse(self, child, id, value):

        try:
            ellipse = {}

            # Is the ellipse representing an owl:intersectionOf statement?
            if "⨅" in value or "owl:intersectionOf" in value:
                ellipse["type"] = "owl:intersectionOf"

            # Is the ellipse representing an owl:unionOf statement?
            elif "⨆" in value or "owl:unionOf" in value:
                ellipse["type"] = "owl:unionOf"

            # Is the ellipse representing an owl:equivalentClass statement?
            elif "≡" in value:
                ellipse["type"] = "owl:equivalentClass"

            # Is the ellipse representing an owl:disjointWith statement?
            elif "⊥" in value:
                ellipse["type"] = "owl:disjointWith"

            # Is the ellipse representing an owl:oneOf statement?
            elif "owl:oneOf" in value:
                ellipse["type"] = "owl:oneOf"
            
            else:
                ellipse["type"] = "blank"
                self.generate_error("An ellipse is blank", id, None, "Ellipses")
            
            ellipse["group"] = []
            ellipse["xml_object"] = child

            self.ellipses[id] = ellipse
            
        except:
            # This exception should not happen if the diagram is generated in drawio.io.
            # However if a user changes manually the xml file generated by drawio.io, it could lead to this error.
            self.generate_error("Unexpected error in an ellipse occurs. Please contact chowlk staff", id, None, "Ellipses")

    # Function to find hexagon elements.
    # The hexagons are stored into a dictionary called "hexagons" whose key is 
    # the xml id of the element and the value is a dictionary called "hexagon".
    # An "hexagon" dictionary stores:
    # 1) the xml object
    # 2) The type of the hexagon, i.e. what the hexagon represents (e.g. owl:oneOf, etc.)
    # 3) The elements id that are related to the hexagon through an arrow
    def add_hexagon(self, child, id, value):

        try:
            hexagon = {}
            
            # Is the hexagon representing an owl:AllDifferent statement?
            if "owl:AllDifferent" in value:
                hexagon["type"] = "owl:AllDifferent"
            
            # Is the hexagon representing an owl:oneOf statement?
            elif "owl:oneOf" in value:
                hexagon["type"] = "owl:oneOf"
            
            # Is the hexagon representing an owl:AllDisjointProperties statement?
            elif "owl:AllDisjointProperties" in value:
                hexagon["type"] = "owl:AllDisjointProperties"

            else:
                self.generate_error("An hexagon is blank", id, None, "Hexagons")
                hexagon['type'] = ''

            # Find the associated concepts to this union / intersection restriction
            hexagon["group"] = []

            hexagon["xml_object"] = child
            self.hexagons[id] = hexagon

        except:
            # This exception should not happen if the diagram is generated in drawio.io.
            # However if a user changes manually the xml file generated by drawio.io, it could lead to this error.
            self.generate_error("Unexpected error in an hexagon occurs. Please contact chowlk staff", id, None, "Hexagons")

    # Function to find elements which represents individuals. These elements are characterized by containing an underlined name.
    # The individuals are stored into a dictionary called "individuals" whose key is the xml id of the element and the value is
    # a dictionary called "individual".
    # An individual dictionary stores:
    # 1) The xml object
    # 2) The individual type
    # 3) The prefix of the name defined in the box
    # 4) The uri of the name defined in the box
    def add_individual(self, child, id, value):
        individual = {}
        value = clean_html_tags(value)

        if "|" in value:
            self.generate_error("Problems in the text of the Individual", id, value, "Individual")
            return

        try:
            individual["prefix"], individual["uri"] = parse_prefix_uri(value)

            if not individual["prefix"] and not individual["uri"]:
                self.generate_error("The individual URI has not a valid identifier", id, value, "Individual")
                return

            individual["xml_object"] = child
            individual["type"] = []

            self.individuals[id] = individual

        except:
            self.generate_error("Problems in the text of the Individual", id, value, "Individual")

    # Function to find "rhombus" elements.
    # The "rhombus" are stored into a dictionary called "rhombuses" whose key is the xml id of the element and its value
    # is a dictionary called "rhombus".
    # A rhombus dictionary stores:
    # 1) The xml object
    # 2) The rhombus type (e.g. object property, etc)
    # 3) The prefix of the name defined in the rhombus
    # 4) The uri of the name defined in the rhombus
    def add_rhombus(self, child, id, html_value):
        rhombus = {}
        value_html_clean = clean_html_tags(html_value) if "value" in child.attrib else None

        try:
            # More than one type can be defined in a rhombus
            # A type is defined between << and >>
            types = re.findall("[<][<]([^>]*)[>][>]", value_html_clean)

            # A rhombus can not be defined as two of the following types at the same time:
            # ObjectProperty, DatatypeProperty or AnnotationProperty
            message = check_rhombus_error_types(types)
            if message:
                self.generate_error(message, id, value_html_clean, "Rhombuses")
                return

            # For main type it is considered: ObjectProperty, DatatypeProperty or AnnotationProperty
            main_type_found = True
            valid_types = []

            # For each type defined in a rhombus, check if it is a valid type
            for t in types:

                # Is the type a non valid type?
                if t not in rhombus_valid_types:
                    self.generate_error("Type <<" + t + ">> can not be defined inside a rhombus", id, value_html_clean, "Rhombuses")

                # Is the type a main type?
                elif main_type_found and (t == 'owl:ObjectProperty' or t == 'owl:DatatypeProperty' or t == 'owl:AnnotationProperty'):
                    rhombus["type"] = t
                    main_type_found = False
                
                else:
                    valid_types.append(t)

            # Has a main type been defined in the rhombus?
            if main_type_found:

                # Is there at least one valid type defined in the rhombus?
                if valid_types:
                    # If at least one of the valid types defined in the rhombus is not 'owl:FunctionalProperty', then
                    # the main type of the rhombus is 'owl:ObjectProperty'. Otherwise, it is impossible to infiere the
                    # main type and the property is declared just as functional.
                    object_property = True

                    # Iterate the valid types
                    for valid_type in valid_types:

                        # Is at least one valid type is not 'owl:FunctionalProperty'?
                        if valid_type != 'owl:FunctionalProperty':
                            rhombus["type"] = 'owl:ObjectProperty'
                            object_property = False
                            break

                    # Are all the valid types 'owl:FunctionalProperty'?
                    if object_property:
                        rhombus["type"] = 'owl:FunctionalProperty'
                
                else:
                    # There is not a single valid type defined in the rhombus
                    self.generate_error("There is not a single valid type defined inside a rhombus", id, value_html_clean, "Rhombuses")
                    return
 
            rhombus["additional_types"] = valid_types

            value = value_html_clean.split("|")[-1].strip()
            value = value.split(">>")[-1].strip()
            
            rhombus["prefix"], rhombus["uri"] = parse_prefix_uri(value)

            if not rhombus["prefix"] and not rhombus["uri"]:
                self.generate_error("The rhombus URI has not a valid identifier", id, value, "Rhombuses")
                return
        
            # Check if the rhombus is deprecated
            if '<strike>' in html_value:
                rhombus['deprecated'] = True
                crossed_text = re.findall("<strike>(.*?)</strike>", html_value)

                if len(crossed_text) > 1:
                    self.generate_error("Problems in the text of the rhombus. To deprecate a rhombus, it is necessary to cross out the full name. In this case, there are no crossed-out characters between crossed-out characters", id, value, "Rhombuses")
                    return

                if value not in crossed_text[0]:
                    self.generate_error("Problems in the text of the rhombus. To deprecate an rhombus, it is necessary to cross out the full name", id, value, "Rhombuses")
                    return
            
            else:
                rhombus['deprecated'] = False

            rhombus["xml_object"] = child

            self.rhombuses[id] = rhombus

        except:
            # This exception should not happen if the diagram is generated in drawio.io.
            # However if a user changes manually the xml file generated by drawio.io, it could lead to this error.
            self.generate_error("Unexpected error in a rhombus occurs. Please contact chowlk staff", id, value_html_clean, "Rhombuses")
    
    # Sometimes the name of an arrow is stored in a different element.
    # This function find the names that are related to an arrow in order to add the name to the corresponding arrow.
    def add_arrow_parent(self, child, value):
        parent = child.attrib["parent"] if "parent" in child.attrib else ""

        if parent and parent != '1' and parent != '0':
            self.arrows_parent[parent] = value
    
    # Function to find concepts and attributes elements.
    # These elements are characterized by being squares or rectangles.
    # Attributes are diferenciated to concepts because these are below a concept (another box).
    # However, in order to differentiate attributes from concepts, first we need to find all the "box" elements.
    # Each box is stored into a dictionary called "boxes" whose key is the xml id of the element and its value is a
    # dictionary called "box".
    # A box dictionary stores:
    # 1) The xml object
    # 2) The name defined inside the box
    # 3) Style (box shape characteristics)
    # 4) box upper left corner
    # 5) box bottom left corner
    def add_box(self, child, id, value, style):
        box = {}

        try:
            box["child"] = child
            box["value"] = value
            box["style"] = style

            # Concepts and attributes shape do not have a specific characteristic to differentiate them.
            # It is neccesary to check if the box upper left corner of a box matches with the bottom left corner
            # of another box.
            p1, p2, p3, p4 = get_corners_rect_child(child)
            box["p1"] = p1
            box["p2"] = p2

            self.boxes[id] = box
                
        except:
            # This exception should not happen if the diagram is generated in drawio.io.
            # However if a user changes manually the xml file generated by drawio.io, it could lead to this error.
            self.generate_error("Unexpected error in a box occurs. Please contact chowlk staff", id, value, "Concepts")

    def add_datatype_property(self, child, html_value, id, style, child2):
        datatype_property = {}
        datatype_property["xml_object"] = child
        # The element is an attrribute
        attributes = []
        value = clean_html_tags(html_value)
        attribute_list = value.split("|")

        # Is it a data value? (e.g. "data value"^^xsd:string, "data value", etc.)
        if len(attribute_list) < 2 and value.startswith("\""):
            return
        
        # In this case is possible that different datatype properties are defined in the same block but not all are marked as deprecated.
        # Therefore, it is necessary to divide the html value by line breaks (<br>) in order to check what properties are deprecated
        html_attribute_list = html_value.split("<br>")
        index = 0
        domain = False if "dashed=1" in style else child2.attrib["id"]

        # Iterate all the datatype properties defined in the same block
        for attribute_value in attribute_list:
            attribute = {}
            range_declared = False
            # attribute_value_cleaned = clean_html_tags(attribute_value)
            attribute_value_cleaned = clean_uri(attribute_value)

            try:

                # get the prefix:uri
                attribute_value_split = attribute_value_cleaned.split(" ")[0].strip()

                # If the datatype has range => remove the last :
                if(attribute_value_split[-1] == ":"):
                    range_declared = True
                    attribute_value_split = attribute_value_split[:-1]

                attribute["prefix"], attribute["uri"] = parse_prefix_uri(attribute_value_split)

                if not attribute["prefix"] and not attribute["uri"]:
                    self.generate_error("The attribute URI has not a valid identifier", id, value, "Attributes") 
                    continue

                # Check if the class is deprecated
                if index < len(html_attribute_list):
                    html_attribute_value = html_attribute_list[index]
                    index += 1

                    if '<strike>' in html_attribute_value:
                        attribute['deprecated'] = True
                        crossed_text = re.findall("<strike>(.*?)</strike>", html_attribute_value)

                        if len(crossed_text) > 1:
                            self.generate_error("Problems in the text of the attribute. To deprecate a datatype property, it is necessary to cross out the full name. In this case, there are no crossed-out characters between crossed-out characters", id, attribute_value, "Attributes")
                            return

                        if attribute_value_split not in crossed_text[0]:
                            self.generate_error("Problems in the text of the attribute. To deprecate a datatype property, it is necessary to cross out the full name", id, attribute_value, "Attributes")
                            return
                    
                    else:
                        attribute['deprecated'] = False
                
                else:
                    attribute['deprecated'] = False
                
                attribute["label"] = create_label(attribute["prefix"], attribute["uri"], "property")

            except:
                self.generate_error("Problems in the text of the attribute", id, attribute_value_cleaned, "Attributes")
                continue

            # Find the datatype
            try:
                if range_declared:

                    datatype_value_split = attribute_value_cleaned.split(" ", 1)[1].strip()
                    # Get the text between '{' and '}'
                    enumeration = re.findall("\{(.*?)\}", datatype_value_split)

                    # Is the user defining an enumerated datatype?
                    if len(enumeration) > 0:
                        attribute["prefix_datatype"] = ''
                        attribute["datatype"] = self.get_datatype_enumeration(enumeration[0], id)
                    
                    else:
                        # The user is defining a datatype

                        #Check if the sentence is <datatype>
                        if datatype_value_split[0] == '<' and datatype_value_split[-1] == '>':
                            if '#' not in datatype_value_split and '/' not in datatype_value_split or (datatype_value_split[-2] == '/' or datatype_value_split[-2] == '#'):
                                self.generate_error("The datatype URI has not a valid identifier", id, value, "Attributes")
                                continue

                            attribute["prefix_datatype"] = ''
                            attribute["datatype"] = datatype_value_split.strip()

                        # Check if the sentence is :datatype
                        elif datatype_value_split[0] == ':':
                            attribute["prefix_datatype"] = ':'
                            attribute["datatype"] = datatype_value_split[1:].strip()

                        #Check if the sentence is prefix:datatype
                        elif ':' in datatype_value_split:
                            final_datatype = datatype_value_split.split(":")
                            attribute["prefix_datatype"] = final_datatype[0].strip()
                            attribute["datatype"] = final_datatype[1].strip()
                        
                        #The sentence is datatype
                        else:
                            attribute["prefix_datatype"] = "xsd"
                            attribute["datatype"] = datatype_value_split.strip()
                
                else:
                    attribute["datatype"] = None

            except:
                self.generate_error("Problems in the datatype of the attribute", id, attribute_value_cleaned, "Attributes")
                continue

            if attribute["datatype"] is None or attribute["datatype"] == "":
                attribute["range"] = False
            else:
                attribute["range"] = True

            attribute["domain"] = domain

            # Existential Universal restriction evaluation
            if "(all)" in attribute_value or "∀" in attribute_value:
                attribute["allValuesFrom"] = True
            else:
                attribute["allValuesFrom"] = False

            if "(some)" in attribute_value or "∃" in attribute_value:
                attribute["someValuesFrom"] = True
            else:
                attribute["someValuesFrom"] = False

            # owl:hasValue
            if "(value)" in attribute_value or "∋" in attribute_value:
                # In these cases the object is a data value of the form
                # "data_value"^^prefix_datatype:datatype
                attribute["hasValue"] = True

            else:
                attribute["hasValue"] = False

            # class_description predicate restriction
            # A named class can be a subClass, an equivalentClass or disjointWith a class restriction
            # When the user wants to declare this relation, it is specified inside the "relation" in diagrams
            if "(sub)" in attribute_value:
                attribute["predicate_restriction"] = "rdfs:subClassOf"
            elif "(eq)" in attribute_value:
                attribute["predicate_restriction"] = "owl:equivalentClass"
            elif "(dis)" in attribute_value:
                attribute["predicate_restriction"] = "owl:disjointWith"
            else:
                attribute["predicate_restriction"] = "rdfs:subClassOf"

            attribute["functional"] = True if "(F)" in attribute_value else False

            # Cardinality restriction evaluation
            try:
                max_min_card = re.findall("\((\S*[.][.]\S*)\)", attribute_value)
                max_min_card = max_min_card[-1] if len(max_min_card) > 0 else None
                if max_min_card is None:
                    attribute["min_cardinality"] = None
                    attribute["max_cardinality"] = None
                else:
                    max_min_card = max_min_card.split("..")
                    attribute["min_cardinality"] = max_min_card[0]
                    attribute["max_cardinality"] = max_min_card[1]
            except:
                self.generate_error("Problems in cardinality definition", id, attribute_value_cleaned, "Attributes")
                continue

            # If min_cardinality == 0 this means it is not necessary to create
            # a min_cardinality restrictions
            if attribute["min_cardinality"] == '0':
                attribute["min_cardinality"] = None

            # If max_cardinality == N this means it is not necessary to create
            # a max_cardinality restrictions
            if attribute["max_cardinality"] == 'N':
                attribute["max_cardinality"] = None

            # Check if min_cardinality represents a non negative integer
            if attribute["min_cardinality"] != None:
                try:
                    aux = float(attribute["min_cardinality"])
                    if not aux.is_integer() or aux < 0:
                        message = ("min_cardinality is " + attribute["min_cardinality"] +
                                    " which is not a non negative integer, in restriction " +
                                    attribute["prefix"] + ":"
                                    + attribute["uri"])
                        attribute["min_cardinality"] = None
                        self.generate_error(message, id, attribute_value_cleaned, "Cardinality-Restrictions")

                except:
                    message = ("min_cardinality is not a number, in attribute "
                                + attribute["prefix"] + ":"
                                + attribute["uri"])
                    attribute["min_cardinality"] = None
                    self.generate_error(message, id, attribute_value_cleaned, "Cardinality-Restrictions")

            if attribute["max_cardinality"] != None:
                # Check if max_cardinality represents a non negative integer
                try:
                    aux = float(attribute["max_cardinality"])
                    if not aux.is_integer() or aux < 0:
                        message = ("max_cardinality is " + attribute["max_cardinality"] +
                                    " which is not a non negative integer, in restriction " +
                                    attribute["prefix"] + ":"
                                    + attribute["uri"])
                        attribute["max_cardinality"] = None
                        self.generate_error(message, id, attribute_value_cleaned, "Cardinality-Restrictions")

                except:
                    message = ("max_cardinality is not a number, in restriction "
                                + attribute["prefix"] + ":"
                                + attribute["uri"])
                    attribute["max_cardinality"] = None
                    self.generate_error(message, id, attribute_value_cleaned, "Cardinality-Restrictions")

            if attribute["min_cardinality"] == attribute["max_cardinality"]:
                attribute["cardinality"] = attribute["min_cardinality"]
                attribute["min_cardinality"] = None
                attribute["max_cardinality"] = None
            else:
                attribute["cardinality"] = None

            # max_cardinality must be greater than min_cardinality
            if(attribute["max_cardinality"] != None and attribute["min_cardinality"] != None
                    and float(attribute["max_cardinality"]) < float(attribute["min_cardinality"])):
                message = ("max_cardinality is lower than min_cardinality" +
                            " in restriction " +
                            attribute["prefix"] + ":"
                            + attribute["uri"])
                attribute["max_cardinality"] = None
                attribute["min_cardinality"] = None
                self.generate_error(message, id, attribute_value_cleaned, "Cardinality-Restrictions")

            # Qualified cardinality restriction evaluation
            try:
                max_min_card = re.findall("\[(\S*[.][.]\S*)\]", attribute_value)
                max_min_card = max_min_card[-1] if len(max_min_card) > 0 else None
                if max_min_card is None:
                    attribute["min_q_cardinality"] = None
                    attribute["max_q_cardinality"] = None
                else:
                    max_min_card = max_min_card.split("..")
                    attribute["min_q_cardinality"] = max_min_card[0]
                    attribute["max_q_cardinality"] = max_min_card[1]
            except:
                self.generate_error("Problems in qualified cardinality definition", id, attribute_value_cleaned, "Attributes")
                continue

            # If min_q_cardinality == 0 this means it is not necessary to create
            # a min_q_cardinality restrictions
            if attribute["min_q_cardinality"] == '0':
                attribute["min_q_cardinality"] = None

            # If max_q_cardinality == N this means it is not necessary to create
            # a max_q_cardinality restrictions
            if attribute["max_q_cardinality"] == 'N':
                attribute["max_q_cardinality"] = None

            # Check if min_q_cardinality represents a non negative integer
            if attribute["min_q_cardinality"] != None:
                try:
                    aux = float(attribute["min_q_cardinality"])
                    if not aux.is_integer() or aux < 0:
                        message = ("min_q_cardinality is " + attribute["min_q_cardinality"] +
                                    " which is not a non negative integer, in restriction " +
                                    attribute["prefix"] + ":"
                                    + attribute["uri"])
                        attribute["min_q_cardinality"] = None
                        self.generate_error(message, id, attribute_value_cleaned, "Cardinality-Restrictions")

                except:
                    message = ("min_q_cardinality is not a number, in attribute "
                                + attribute["prefix"] + ":"
                                + attribute["uri"])
                    attribute["min_q_cardinality"] = None
                    self.generate_error(message, id, attribute_value_cleaned, "Cardinality-Restrictions")

            if attribute["max_q_cardinality"] != None:
                # Check if max_q_cardinality represents a non negative integer
                try:
                    aux = float(attribute["max_q_cardinality"])
                    if not aux.is_integer() or aux < 0:
                        message = ("max_q_cardinality is " + attribute["max_q_cardinality"] +
                                    " which is not a non negative integer, in restriction " +
                                    attribute["prefix"] + ":"
                                    + attribute["uri"])
                        attribute["max_q_cardinality"] = None
                        self.generate_error(message, id, attribute_value_cleaned, "Cardinality-Restrictions")

                except:
                    message = ("max_q_cardinality is not a number, in restriction "
                                + attribute["prefix"] + ":"
                                + attribute["uri"])
                    attribute["max_q_cardinality"] = None
                    self.generate_error(message, id, attribute_value_cleaned, "Cardinality-Restrictions")

            if attribute["min_q_cardinality"] == attribute["max_q_cardinality"]:
                attribute["q_cardinality"] = attribute["min_q_cardinality"]
                attribute["min_q_cardinality"] = None
                attribute["max_q_cardinality"] = None
            else:
                attribute["q_cardinality"] = None

            # max_q_cardinality must be greater than min_q_cardinality
            if(attribute["max_q_cardinality"] != None and attribute["min_q_cardinality"] != None
                    and float(attribute["max_q_cardinality"]) < float(attribute["min_q_cardinality"])):
                message = ("max_q_cardinality is lower than min_q_cardinality" +
                            " in restriction " +
                            attribute["prefix"] + ":"
                            + attribute["uri"])
                attribute["max_q_cardinality"] = None
                attribute["min_q_cardinality"] = None
                self.generate_error(message, id, attribute_value_cleaned, "Cardinality-Restrictions")

            attributes.append(attribute)

        datatype_property["attributes"] = attributes
        datatype_property["concept_associated"] = child2.attrib["id"]
        self.datatype_properties[id] = datatype_property

    # Function to add an anonymous class
    def add_anonymous_class(self, child, id):
        anonymous_class = {}
        anonymous_class["xml_object"] = child
        anonymous_class["relations"] = []
        anonymous_class["attributes"] = []
        self.anonymous_classes[id] = anonymous_class
    
    # Function to add an anonymous individual
    def add_anonymous_individual(self, child, id):
        anonymous_individual = {}
        anonymous_individual["xml_object"] = child
        anonymous_individual["relations"] = []
        self.anonymous_individuals[id] = anonymous_individual

    # This function store each of the selected boxes into a dictionary called "concepts" whose
    # key is the xml object identifier and the value is a dictionary called "concept".
    # A concept dictionary stores:
    # 1) The xml object
    # 2) The prefix of the name defined in the box
    # 3) The uri of the name defined in the box
    # 4) An auto generated label
    def add_class(self, html_value, id, child):
        ontology_class = {}
        # First we have to verify they are actually concepts because it could be the case
        # that an user wants to define an attribute but it is not attached to a concept
        value = clean_html_tags(html_value).strip()

        # One way is to verify breaks in the text
        if "|" in value:
            self.generate_error("Problems in text of the Concept", id, value, "Concepts")
            return

        # Other option is to verify things like functionality, some, all, etc.
        if "(F)" in value or "(some)" in value or "(all)" in value or "∀" in value or "∃" in value:
            self.generate_error("Attributes not attached to any concept", id, value, "Attributes")
            return

        # If datatype is mentioned
        if len(value.split(":")) > 2:

            if not ("&quot;" in value or "\"" in value):
                self.generate_error("Attributes not attached to any concept", id, value, "Attributes")
            return

        # If cardinality is indicated
        if len(value.split("..")) > 1:
            self.generate_error("Attributes not attached to any concept", id, value, "Attributes")
            return

        # Is it a data value? (e.g. "data value"^^xsd:string, "data value", etc.)
        if "\"" in value:
            return

        # Identify the prefix and suffix define in the name of the box
        try:

            ontology_class["prefix"], ontology_class["uri"] = parse_prefix_uri(value)

            if not ontology_class["prefix"] and not ontology_class["uri"]:
                self.generate_error("The concept URI has not a valid identifier", id, value, "Concepts")
                return

            ontology_class["label"] = create_label(ontology_class["prefix"], ontology_class["uri"], "class")

        except:
            self.generate_error("Problems in text of the concept", id, value, "Concepts")
            return
        
        # Check if the class is deprecated
        if '<strike>' in html_value:
            ontology_class['deprecated'] = True
            crossed_text = re.findall("<strike>(.*?)</strike>", html_value)

            if len(crossed_text) > 1:
                self.generate_error("Problems in the text of the concept. To deprecate a class, it is necessary to cross out the full name. In this case, there are no crossed-out characters between crossed-out characters", id, value, "Concepts")
                return

            if value not in crossed_text[0]:
                self.generate_error("Problems in the text of the concept. To deprecate a class, it is necessary to cross out the full name", id, value, "Concepts")
                return
        
        else:
            ontology_class['deprecated'] = False
        
        ontology_class["xml_object"] = child
        self.classes[id] = ontology_class

    # This function store the object identifier of each relation with the same name.
    # For name it is understood the combination prefix:suffix
    def store_relation_name(self, id, prefix, suffix):

        # Is there a defined prefix which is not the empty prefix?
        if prefix and prefix != ':':
            prefix += ':'

        name = prefix + suffix

        # Is there a relation with the same name?
        if name in self.arrows_name:
            self.arrows_name[name].append(id)

        else:
            self.arrows_name[name] = [id]

    # This function finds the property values.
    # A property value is defined as "dataValue"^^type, "datatype"@language or "datatype", where "type" is defined as "prefix:suffix" or "suffix".
    # These elements are stored in a dictionary called "property_values" whose key is the xml id element and the value is a dictionary called "property_value".
    # The "property_value" dictionary stores:
    # 1) The xml object
    # 2) The value of the datatype
    # 3) The type of the dataype
    # 4) The language of the datatype (in case of being a literal)
    def add_property_value(self, id, value, child):

        value = clean_html_tags(value)

        if "&quot;" in value or "\"" in value:
            property_value = {}
            property_value["type"] = None
            property_value["lang"] = None

            try:
                # Finding the value
                if "&quot;" in value:
                    property_value["value"] = value.split("&quot;")[1]

                elif "\"" in value:
                    reg_exp = '"(.*?)"'
                    property_value["value"] = re.findall(reg_exp, value)[0]

                # Finding the type
                if "^^" in value:
                    property_value["type"] = value.split("^^")[-1]

                elif "@" in value:
                    property_value["lang"] = value.split("@")[-1]

            except:
                self.generate_error("Problems in the text of the literal", id, value, "Individual")
                return

            property_value["xml_object"] = child

            self.property_values[id] = property_value

    # This function generate an error and stores it in the corresponding category
    def generate_error(self, message, id, value, type):
        error = {}
        error['message'] = message
        if id != None:
            error['shape_id'] = id
            
        if value != None:
            error['value'] = value

        self.errors[type].append(error)
    
    # This function generate a warning and stores it in the corresponding category
    def generate_warning(self, message, id, value, type):
        warning = {}
        warning['message'] = message
        if id != None:
            warning['shape_id'] = id
            
        if value != None:
            warning['value'] = value

        self.warnings[type].append(warning)
    
    # This function add more information to the "relation" dictionary.
    # Specifically the following information is added:
    # 1) type of the relation (e.g. object property, subClassOf, etc.)
    # 2) domain of the relation (i.e. if the user wants to declare a domain for an object property)
    # 3) range of the relation (i.e. if the user wants to declare a range for an object property)
    # 4) Universal restrictions (e.g. allValuesFrom, someValuesFrom, etc.)
    # 5) predicate restriction (i.e. specify the predicate of a restriction triple)
    # 6) additional property types (e.g. functional, symmetric, etc.)
    # 7) The uri of the name defined in the arrow
    # 8) An auto generated label
    def add_value_to_arrow(self, relation, html_value, style, id):
        value = clean_html_tags(html_value)

        # Has the arrow a source element from which it departs?
        if relation["source"] is None:
            self.generate_error("The origin of the arrow is not connected to any shape, please check this.", id, value, "Arrows")

        # Has the arrow a target element on which it ends?
        if relation["target"] is None:
            self.generate_error("The end of the arrow is not connected to any shape, please check this.", id, value, "Arrows")

        # Detection of special type of edges
        edge_type_founded = False

        for edge_type in edge_types:
            # This edge is not useful beyond that construction (edge_type)
            if edge_type in value:
                relation["type"] = edge_type
                self.arrows[id] = relation
                edge_type_founded = True
                break

        if edge_type_founded:
            # In the case of special relations it not neccesary to add more information about the arrow
            # because in these cases chowlk just needed to know its source and target
            return

        # Domain Range evaluation
        if "dashed=1" in style:
            if "startArrow=oval" not in style or "startFill=0" in style:
                relation["domain"] = False
                relation["range"] = False
            elif "startFill=1" in style:
                relation["domain"] = relation["source"]
                relation["range"] = False

        else:
            if "startArrow=oval" not in style or "startFill=1" in style:
                relation["domain"] = relation["source"]
                relation["range"] = relation["target"]
            elif "startFill=0" in style:
                relation["domain"] = False
                relation["range"] = relation["target"]

        # Existential Universal restriction evaluation
        if "allValuesFrom" in value or "(all)" in value or "∀" in value:
            relation["allValuesFrom"] = True
        else:
            relation["allValuesFrom"] = False

        if "someValuesFrom" in value or "(some)" in value or "∃" in value:
            relation["someValuesFrom"] = True
        else:
            relation["someValuesFrom"] = False

        # owl:hasValue
        if "hasValue" in value or "(value)" in value or "∋" in value:
            relation["hasValue"] = True
        else:
            relation["hasValue"] = False

        # class_description predicate restriction
        # A named class can be a subClass, an equivalentClass or disjointWith a class restriction
        # When the user wants to declare this relation, it is specified inside the arrow name in the xml
        if "(sub)" in value:
            relation["predicate_restriction"] = "rdfs:subClassOf"
        elif "(eq)" in value:
            relation["predicate_restriction"] = "owl:equivalentClass"
        elif "(dis)" in value:
            relation["predicate_restriction"] = "owl:disjointWith"
        else:
            relation["predicate_restriction"] = "rdfs:subClassOf"

        # Property restriction evaluation
        relation["functional"] = True if "(F)" in value else False
        relation["inverse_functional"] = True if "(IF)" in value else False
        relation["transitive"] = True if "(T)" in value else False
        relation["symmetric"] = True if "(S)" in value else False
        relation["reflexive"] = True if "(R)" in value else False
        relation["asymmetric"] = True if "(A)" in value else False
        relation["irreflexive"] = True if "(IR)" in value else False
        
        # Obtain the prefix and suffix defined in the arrrow name
        try:
            uri = clean_uri(value)

            #uri = uri.split("|")[-1].strip().split(">>")[-1].strip()
            uri = uri.split("|")[-1].strip()

            if ">>" in uri:
                self.generate_error("Problems in the text of the arrow", id, value, "Arrows")
                return

            relation["prefix"], relation["uri"] = parse_prefix_uri(uri)

            # Has the user defined a prefix and a suffix in the arrow?
            if not relation["prefix"] and not relation["uri"]:
                self.generate_error("The relation URI has not a valid identifier", id, value, "Arrows")
                return

            relation["label"] = create_label(relation["prefix"], relation["uri"], "property")

        except:
            self.generate_error("Problems in the text of the arrow", id, value, "Arrows")
            return
        
        # Check if the arrow is deprecated
        if '<strike>' in html_value:
            relation['deprecated'] = True
            crossed_text = re.findall("<strike>(.*?)</strike>", html_value)

            if len(crossed_text) > 1:
                self.generate_error("Problems in the text of the arrow. To deprecate an arrow, it is necessary to cross out the full name. In this case, there are no crossed-out characters between crossed-out characters", id, value, "Arrows")
                return

            if uri not in crossed_text[0]:
                self.generate_error("Problems in the text of the arrow. To deprecate an arrow, it is necessary to cross out the full name", id, value, "Arrows")
                return
        
        else:
            relation['deprecated'] = False

        # Cardinality restriction evaluation
        try:
            # Find (N1..N2) in the arrow name
            max_min_card = re.findall("\((\S*[.][.]\S*)\)", value)
            max_min_card = max_min_card[-1] if len(max_min_card) > 0 else None

            if max_min_card is None:
                relation["min_cardinality"] = None
                relation["max_cardinality"] = None
            else:
                max_min_card = max_min_card.split("..")
                relation["min_cardinality"] = max_min_card[0]
                relation["max_cardinality"] = max_min_card[1]

        except:
            self.generate_error("Problems in cardinality definition", id, value, "Arrows")
            return

        # If min_cardinality == 0 this means it is not necessary to create
        # a min_cardinality restrictions
        if relation["min_cardinality"] == '0':
            relation["min_cardinality"] = None

        # If max_cardinality == N this means it is not necessary to create
        # a max_cardinality restrictions
        if relation["max_cardinality"] == 'N':
            relation["max_cardinality"] = None

        # Check if min_cardinality represents a non negative integer
        if relation["min_cardinality"] != None:
            try:
                aux = float(relation["min_cardinality"])
                if not aux.is_integer() or aux < 0:
                    message = f'min_cardinality is {relation["min_cardinality"]} which is not a non negative integer, in restriction {relation["prefix"]}:{relation["uri"]}'
                    relation["min_cardinality"] = None
                    self.generate_error(message, id, value, "Cardinality-Restrictions")

            except:
                message = f'min_cardinality is not a number, in restriction {relation["prefix"]}:{relation["uri"]}'
                relation["min_cardinality"] = None
                self.generate_error(message, id, value, "Cardinality-Restrictions")

        if relation["max_cardinality"] != None:
            # Check if max_cardinality represents a non negative integer
            try:
                aux = float(relation["max_cardinality"])
                if not aux.is_integer() or aux < 0:
                    message = f'max_cardinality is {relation["max_cardinality"]} which is not a non negative integer, in restriction {relation["prefix"]}:{relation["uri"]}'
                    relation["max_cardinality"] = None
                    self.generate_error(message, id, value, "Cardinality-Restrictions")

            except:
                message = f'max_cardinality is not a number, in restriction {relation["prefix"]}:{relation["uri"]}'
                relation["max_cardinality"] = None
                self.generate_error(message, id, value, "Cardinality-Restrictions")

        # Check if the user is defining an exact cardinality
        if relation["min_cardinality"] == relation["max_cardinality"]:
            relation["cardinality"] = relation["min_cardinality"]
            relation["max_cardinality"] = None
            relation["min_cardinality"] = None
        else:
            relation["cardinality"] = None

        # max_cardinality must be greater than min_cardinality
        if(relation["max_cardinality"] != None and relation["min_cardinality"] != None and float(relation["max_cardinality"]) < float(relation["min_cardinality"])):
            message = ("max_cardinality is lower than min_cardinality" +
                        " in restriction " + relation["prefix"] + ":"
                        + relation["uri"])
            relation["max_cardinality"] = None
            relation["min_cardinality"] = None
            self.generate_error(message, id, value, "Cardinality-Restrictions")
        
        # Qualified cardinality restriction evaluation
        try:
            # Find [N1..N2] in the arrow name
            max_min_card = re.findall("\[(\S*[.][.]\S*)\]", value)
            max_min_card = max_min_card[-1] if len(max_min_card) > 0 else None

            if max_min_card is None:
                relation["min_q_cardinality"] = None
                relation["max_q_cardinality"] = None
            else:
                max_min_card = max_min_card.split("..")
                relation["min_q_cardinality"] = max_min_card[0]
                relation["max_q_cardinality"] = max_min_card[1]

        except:
            self.generate_error("Problems in qualified cardinality definition", id, value, "Arrows")
            return

        # If min_q_cardinality == 0 this means it is not necessary to create
        # a min_q_cardinality restrictions
        if relation["min_q_cardinality"] == '0':
            relation["min_q_cardinality"] = None

        # If max_q_cardinality == N this means it is not necessary to create
        # a max_q_cardinality restrictions
        if relation["max_q_cardinality"] == 'N':
            relation["max_q_cardinality"] = None
        
        # Check if min_q_cardinality represents a non negative integer
        if relation["min_q_cardinality"] != None:
            try:
                aux = float(relation["min_q_cardinality"])
                if not aux.is_integer() or aux < 0:
                    message = f'min_q_cardinality is {relation["min_q_cardinality"]} which is not a non negative integer, in restriction {relation["prefix"]}:{relation["uri"]}'
                    relation["min_q_cardinality"] = None
                    self.generate_error(message, id, value, "Cardinality-Restrictions")

            except:
                message = f'min_q_cardinality is not a number, in restriction {relation["prefix"]}:{relation["uri"]}'
                relation["min_q_cardinality"] = None
                self.generate_error(message, id, value, "Cardinality-Restrictions")

        if relation["max_q_cardinality"] != None:
            # Check if max_q_cardinality represents a non negative integer
            try:
                aux = float(relation["max_q_cardinality"])
                if not aux.is_integer() or aux < 0:
                    message = f'max_q_cardinality is {relation["max_q_cardinality"]} which is not a non negative integer, in restriction {relation["prefix"]}:{relation["uri"]}'
                    relation["max_q_cardinality"] = None
                    self.generate_error(message, id, value, "Cardinality-Restrictions")

            except:
                message = f'max_q_cardinality is not a number, in restriction {relation["prefix"]}:{relation["uri"]}'
                relation["max_q_cardinality"] = None
                self.generate_error(message, id, value, "Cardinality-Restrictions")
        
        # Check if the user is defining an exact qualified cardinality
        if relation["min_q_cardinality"] == relation["max_q_cardinality"]:
            relation["q_cardinality"] = relation["min_q_cardinality"]
            relation["max_q_cardinality"] = None
            relation["min_q_cardinality"] = None
        else:
            relation["q_cardinality"] = None

        # max_q_cardinality must be greater than min_cardinality
        if(relation["max_q_cardinality"] != None and relation["min_q_cardinality"] != None and float(relation["max_q_cardinality"]) < float(relation["min_q_cardinality"])):
            message = ("max_q_cardinality is lower than min_q_cardinality" +
                        " in restriction " + relation["prefix"] + ":"
                        + relation["uri"])
            relation["max_q_cardinality"] = None
            relation["min_q_cardinality"] = None
            self.generate_error(message, id, value, "Cardinality-Restrictions")

        prefix = relation["prefix"]
        uri = relation['uri']

        # Is a default annotation property? (i.e. rdfs:isDefinedBy, rdfs:comment, rdfs:label or rdfs:seeAlso)
        if 'rdfs' == prefix and (uri == 'isDefinedBy' or uri == 'comment' or uri == 'label' or uri == 'seeAlso'):
            relation["type"] = "owl:AnnotationProperty"

        # Is a default annotation property (i.e. owl:versionInfo)
        elif 'owl' == prefix and (uri =='versionInfo'):
            relation["type"] = "owl:AnnotationProperty"

        else:
            # It is an object property
            relation["type"] = "owl:ObjectProperty"

        # Store the name and identifier of the arrow
        self.store_relation_name(id, relation["prefix"], relation["uri"])

        self.arrows[id] = relation
    
    def get_datatype_enumeration(self, enumeration, d_p_block_id):
        datatype = '[ rdf:type rdfs:Datatype ; owl:oneOf'
        data_values = enumeration.split(',')

        if len(data_values) > 0:
            text1 = ""
            text2 = ""

            for data_value in data_values:
                prepare_value = self.prepare_data_value(data_value.strip(), d_p_block_id)

                if prepare_value is not None:
                    text1 += f' [ rdf:type rdf:List ; rdf:first {prepare_value}; rdf:rest'
                    text2 += ' ]'
            
            if text1:
                datatype += f'{text1}  rdf:nil {text2} ]'
            
            else:
                datatype = None
        
        else:
            prepare_value = self.prepare_data_value(enumeration.strip(), d_p_block_id)

            if prepare_value is not None:
                datatype += f' [ rdf:type rdf:List ; rdf:first {prepare_value}; rdf:rest rdf:nil ]'
            
            else:
                datatype = None

        return datatype

    def prepare_data_value(self, data_value, d_p_block_id):
        # Divide a data value into its value and type
        try:

            # Finding the value
            if "&quot;" in data_value:
                value_split = data_value.split("&quot;")

                if len(value_split) > 2:
                    self.generate_error("Problems in the text of a data value defined in an enumeration datatype. Data values must be separated by ','", d_p_block_id, data_value, "Attributes")
                    return None

                value = value_split[1]

            elif "\"" in data_value:
                value_split = re.findall('"(.*?)"', data_value)

                if len(value_split) > 1:
                    self.generate_error("Problems in the text of a data value defined in an enumeration datatype. Data values must be separated by ','", d_p_block_id, data_value, "Attributes")
                    return None

                value = value_split[0]
            
            else:
                self.generate_error("Problems in the text of a data value defined in an enumeration datatype. Data values must be defined between '\"'", d_p_block_id, data_value, "Attributes")
                return None

            type = None
            lang = None

            # Finding the type
            if "^^" in data_value:
                type = data_value.split("^^")[-1]

            elif "@" in data_value:
                lang = data_value.split("@")[-1]
            
            elif data_value[-1] != '"' and not data_value.endswith('&quot;'):
                self.generate_error("Problems in the text of a data value defined in an enumeration datatype. The datatype of a data value must be defined after '^^'", d_p_block_id, data_value, "Attributes")
        
        except:
            self.generate_error("Problems in the text of a data value defined in an enumeration datatype", d_p_block_id, data_value, "Attributes")
            return None

        # Is a datatype specified in the data value?
        if type is not None:
            # Is the datatype specified through a prefix:uri?
            if ":" in type:
                object = "\"" + value + "\"" + "^^" + type
            
            else:
                # The default prefix is xsd
                object = "\"" + value + "\"" + "^^xsd:" + type
        
        # Is a language specified in the data value?
        elif lang is not None:
            # The data value is a literal
            object = "\"" + value + "\"" + "@" + lang
        
        else:
            # The data value is a literal
            object = "\"" + value + "\""

        return object
    
# This function check if there are two main types defined inside a rhombus.
# For main types it is understood: ObjectProperty, DatatypeProperty or AnnotationProperty
def check_rhombus_error_types(types):
    if "owl:ObjectProperty" in types and "owl:DatatypeProperty" in types:
        return "A rhombus can not be defined as Object Property and Datatype Property at the same time"
            
    elif "owl:ObjectProperty" in types and "owl:AnnotationProperty" in types:
        return "A rhombus can not be defined as Object Property and Annotation Property at the same time"

    elif "owl:DatatypeProperty" in types and "owl:AnnotationProperty" in types:
        return "A rhombus can not be defined as Datatype Property and Annotation Property at the same time"
    
    return ""