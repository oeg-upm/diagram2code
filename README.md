![Logo](https://github.com/oeg-upm/Chowlk/blob/webservice/app/static/images/logos/logo.png)

# Chowlk Converter
Tool to transform ontology conceptualizations made with diagrams.net into OWL code.

The conceptualizations should follow the <a href="https://chowlk.linkeddata.es/notation.html">Chowlk visual notation</a>. Please visit the specification for more details.

Citing Chowlk: If you used Chowlk in your work, please cite the [ESWC paper](https://2022.eswc-conferences.org/wp-content/uploads/2022/05/paper_90_Chavez-Feria_et_al.pdf):

```bib
@InProceedings{10.1007/978-3-031-06981-9_20,
author="Ch{\'a}vez-Feria, Serge
and Garc{\'i}a-Castro, Ra{\'u}l
and Poveda-Villal{\'o}n, Mar{\'i}a",
editor="Groth, Paul
and Vidal, Maria-Esther
and Suchanek, Fabian
and Szekley, Pedro
and Kapanipathi, Pavan
and Pesquita, Catia
and Skaf-Molli, Hala
and Tamper, Minna",
title="Chowlk: from UML-Based Ontology Conceptualizations to OWL",
booktitle="The Semantic Web",
year="2022",
publisher="Springer International Publishing",
address="Cham",
pages="338--352"
}
```

## How to use the tool

You have several options to use this tool.

### 1. The web application:

1. Go to https://chowlk.linkeddata.es/ web application.
2. Download the Chowlk template.
  
  * Complete version of the template:
    https://github.com/oeg-upm/chowlk_spec/blob/master/resources/chowlk-library-complete.xml

  * Lightweight version of the template:
    https://github.com/oeg-upm/chowlk_spec/blob/master/resources/chowlk-library-lightweight.xml
     
3. In diagrams.net go to File > Open Library from > Device ...
4. Select the library downloaded.
5. Make your conceptualization using the blocks that will appear on the side bar.
6. Download the diagram in xml format.
7. Drag and drop your diagram in the Service dropping area and download your TTL file.

### 2. The API:

The following command line will return the ontology in Turtle format.

```bash
curl -F data=@path_to_diagram/diagram.xml https://chowlk.linkeddata.es/api
```

where path_to_diagram can be a relative path (e.g. diagrams/diagram.xml) or an absolute path (e.g. /home/user/diagrams/diagram.xml).

The service will return the following dictionary:

```json
{
  "ttl_data": "@prefix ns: ...",
  "new_namespaces": {"ns1": "https://namespace1.com#", "ns2": "https://namespace2.com#"},
  "errors": {"Concepts": [{"message": "Problem in text", "shape_id": "13", "value": "ns:Building Element"}],
             "Attributes": [{"message": "Problem in cardinality", "shape_id": 45, "value": "ns:ifcIdentifier"}]},
  "xml_error_generated": true,
  "xml_error_file": "<mxfile ...",
  "warnings": {"Base": [{"message": "A base has not been declared. The first namespace has been taken as base"}]}
}
```

* **ttl_data:** Contains the ontology generated from the diagram in Turtle format. It is returned in string format.
* **new_namespaces:** Contains the new namespaces created for the ontology. These are the prefixes found in the model but not declared in the namespace block of the diagram. The returned object is a dictionary with the following format: {"prefix1": "namespace1", "prefix2": "namespace2"}.
* **errors:** Contains the errors found in the ontology diagram, organised by category. The keywords are the categories and the value for these keywords is an array that may contain objects that have the following structure:

```json
{
  "message": "Some message related to the problem",
  "shape_id": "An integer id that identify the problematic shape in the diagram",
  "value": "the actual text related with the shape"
}
```
* **xml_error_generated:** Specifies whether an xml file highlighting the errors has been generated.
* **xml_error_file:** It contains an xml file in which the shapes involved in an error are marked in red. In addition, for each error a new shapes is generated containing a message explaining the error. This xml file can be uploaded to drawio.io.
* **warnings:** Contains the warnings found in the ontology diagram, organised by category. The keywords are the categories and the value for these keywords is an array that may contain objects that have the following structure:

```json
{
  "message": "Some message related to the problem",
  "shape_id": "An integer id that identify the problematic shape in the diagram",
  "value": "the actual text related with the shape"
}
```

### 3. Running it from docker:
### Copy the project:
```bash
git clone https://github.com/oeg-upm/Chowlk.git
git checkout webservice
```
### Docker:
1. Intall and run Docker Desktop
2. Open a command line located in the Chowlk repository and execute:
```bash
docker compose up
```
3. Open a web browser and go to localhost:5000

### 4. Running it from source:

### Copy the project:
```bash
git clone https://github.com/oeg-upm/Chowlk.git
git checkout webservice
```
### Install python 3.12.6

### Requirements:
```bash
pip install -r requirements.txt
```

### To convert a diagram:

positional arguments:

    diagram_path          the path where the diagram is located
  
    output_path           the desired location for the generated ontology

options:

    -h, --help            show this help message and exit
  
    --xml_error_path XML_ERROR_PATH            the desired location for the xml file with the marked errors found in the diagram
  
    --type TYPE           ontology or rdf data
  
    --format FORMAT       file format: ttl or xml

* If the desired format is ttl:
```bash
python converter.py path/to/diagram.xml output/path/ontology.ttl --type ontology --format ttl
```

* If the desired format is ttl and the path to the xml error is indicated:
```bash
python converter.py path/to/diagram.xml output/path/ontology.ttl --xml_error_path output/path/error_xml.xml --type ontology --format ttl
```

* If the desired format is rdf/xml:
```bash
python converter.py path/to/diagram.xml output/path/ontology.xml --type ontology --format xml
```

* If the desired format is rdf/xml and the path to the xml error is indicated:
```bash
python converter.py path/to/diagram.xml output/path/ontology.xml --xml_error_path output/path/error_xml.xml --type ontology --format xml
```

### To run the app locally:
```bash
python entrypoint.py
```

## Publications

* Chávez-Feria, S., García-Castro, R., Poveda-Villalón, M. (2022). Chowlk: from UML-Based Ontology Conceptualizations to OWL. In: , et al. The Semantic Web. ESWC 2022. Lecture Notes in Computer Science, vol 13261. Springer, Cham. https://doi.org/10.1007/978-3-031-06981-9_20

* Poveda-Villalón, M., Chávez-Feria, S., Carulli-Pérez, S., & García-Castro, R. (2023). Towards a UML-based notation for OWL ontologies. Proceedings of the 8th International Workshop on the Visualization and Interaction for Ontologies, Linked Data and Knowledge Graphs co-located with the 22nd International Semantic Web Conference (ISWC 2023). https://ceur-ws.org/Vol-3508/paper2.pdf

* Chávez-Feria, S., García-Castro, R., Poveda-Villalón, M. (2021). <i>Converting UML-based ontology conceptualizations to OWL with Chowlk. In ESWC (Poster and Demo Track)</i>

## Contact
* Maria Poveda-Villalón (chowlk@delicias.dia.fi.upm.es)
