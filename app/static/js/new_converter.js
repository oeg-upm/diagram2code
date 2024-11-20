// The service box
const dragDropArea = document.getElementById('drag-drop-area');
// The file that a user is going to drop/select in the service box
const input = dragDropArea.querySelector('#fileElem');
// The text displayed inside the service box before the ttl has been generated (name of the file selected or instructions for the user)
const inputName = dragDropArea.querySelector('#drag-text');
// Submit button
const submitButton = document.getElementById('submit');
// Download button
const downloadButton = document.getElementById('download');
// The text displayed inside the service box after the ttl has been generated
const responseText = document.getElementById('response');

//Button to download an xml file which helps users to detect the errors in their diagrams
const downloadButtonXmlErrorFile = document.getElementById('download-xml-errors');

// Error/warning sections
const errorReport = document.getElementById('error-report');
const warningReport = document.getElementById('warning-report');

//Warning accordions
const baseItem = document.getElementById('base-item');
const baseBody = document.getElementById('base-body');

const ontologyUriItem = document.getElementById('ontology-uri-item');
const ontologyUriBody = document.getElementById('ontology-uri-body');

const restrictionsWItem = document.getElementById('restrictions-w-item');
const restrictionsWBody = document.getElementById('restrictions-w-body');

const deprecatedItem = document.getElementById('deprecated-item');
const deprecatedBody = document.getElementById('deprecated-body');

//Special error accordions
const xmlErrors = document.getElementById('xml-errors');

const newNamespaces = document.getElementById('new-namespaces');
const textNamespace = document.getElementById('textNamespaces');

//Error accordions
const conceptsItem = document.getElementById('concepts-item');
const conceptsBody = document.getElementById('concepts-body');

const arrowsItem = document.getElementById('arrows-item');
const arrowsBody = document.getElementById('arrows-body');

const ellipsesItem = document.getElementById('ellipses-item');
const ellipsesBody = document.getElementById('ellipses-body');

const attributesItem = document.getElementById('attributes-item');
const attributesBody = document.getElementById('attributes-body');

const namespacesItem = document.getElementById('namespaces-item');
const namespacesBody = document.getElementById('namespaces-body');

const metadataItem = document.getElementById('metadata-item');
const metadataBody = document.getElementById('metadata-body');

const rhombusesItem = document.getElementById('rhombuses-item');
const rhombusesBody = document.getElementById('rhombuses-body');

const individualItem = document.getElementById('individual-item');
const individualBody = document.getElementById('individual-body');

const hexagonsItem = document.getElementById('hexagons-item');
const hexagonsBody = document.getElementById('hexagons-body');

const cardinalityRestrictionsItem = document.getElementById('cardinalityRestrictions-item');
const cardinalityRestrictionsBody = document.getElementById('cardinalityRestrictions-body');

const intersectionOfItem = document.getElementById('intersectionOf-item');
const intersectionOfBody = document.getElementById('intersectionOf-body');

const oneOfItem = document.getElementById('oneOf-item');
const oneOfBody = document.getElementById('oneOf-body');

const complementOfItem = document.getElementById('complementOf-item');
const complementOfBody = document.getElementById('complementOf-body');

const unionOfItem = document.getElementById('unionOf-item');
const unionOfBody = document.getElementById('unionOf-body');

const relationItem = document.getElementById('relation-item');
const relationBody = document.getElementById('relation-body');

const annotationPropertyItem = document.getElementById('annotation-property-item');
const annotationPropertyBody = document.getElementById('annotation-property-body');

const baseErrorItem = document.getElementById('base-error-item');
const baseErrorBody = document.getElementById('base-error-body');

const syntaxItem = document.getElementById('syntax-item');
const syntaxBody = document.getElementById('syntax-body');

const serverErrorItem = document.getElementById('server-error-item');
const serverErrorBody = document.getElementById('server-error-body');



let response;
let file;
let loadFile = false;
let loadTransformedDiagram = false;
let xmlErrorFile;
let loadXmlErrorFile = false;

//Drag enter event handler
//If the drag file enter the box => the box color is white and
//it is detected as a new file
dragDropArea.addEventListener('dragenter', (e) => {
    e.preventDefault();
    loadFile = false;
    responseText.style.display = 'none';
    inputName.style.display = 'block';
    dragDropArea.style.backgroundColor = 'white';
    inputName.innerHTML = 'Drag and drop your diagram or click to choose your file';
});

//Drag leave event handler
//If the drag file leave the box => the box color is white
dragDropArea.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dragDropArea.style.backgroundColor = 'white';
    inputName.innerHTML = 'Drag and drop your diagram or click to choose your file';
});

//Drag over event handler
//While the drag file is on the box => the box color is grey
dragDropArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    dragDropArea.style.backgroundColor = '#ECECEC';
    inputName.innerHTML = 'Release your diagram';
});

//Mouseover event handler
//While the mouse is on the box => the mouse pointer change in
//order to indicate to the user that they can click the box
dragDropArea.addEventListener('mouseover', ()=>{
    dragDropArea.style.cursor = 'pointer';
});

//Click event handler
//If the user click on the box => the user can select a local file to upload
dragDropArea.addEventListener('click', (e)=>{
    input.click();
});

//Change event handler
//Each time a user select a file => indicate to the user the name of the file
input.addEventListener('change', (e) => {
    loadFile = false;
    responseText.style.display = 'none';
    inputName.innerHTML = 'Drag and drop your diagram or click to choose your file';
    inputName.style.display = 'block';
    checkFiles(input.files);
});

//Drop event handler
//Each time a user drop a file => indicate to the user the name of the file
dragDropArea.addEventListener('drop', (e) => {
    e.preventDefault();
    dragDropArea.style.backgroundColor = 'white';
    inputName.innerHTML = 'Drag and drop your diagram or click to choose your file';
    checkFiles(e.dataTransfer.files);
});

//Function to check the number of files
function checkFiles(files){
    if (files.length === undefined) {
        //There is just one file
        processFile(files);
    } else if (files.length === 1) {
        //There is just one file
        processFile(files[0]);
    } else {
        //There is more than one file. Just the first file is processed
        alert('Only the first diagram is going to be processed');
        processFile(files[0]);
    }
}

//Function to show the name of the diagram the user selected, check its extension
//and load the file in memory
function processFile(f){
    if (f != undefined && f.type == 'text/xml'){
        //File extension correct'
        inputName.innerHTML = '<b>"' + f.name + '"</b>' + ' selected';
        file = f;
        loadFile = true;
    } else {
        alert('The extension of the diagram must be xml');
    }
}

//Click event handler for the button 'submit'
//If there is not a file loaded => warn the user
//If there is a file loaded => transform the diagram
submitButton.addEventListener('click', (e) => {
    //Submit
    if (loadFile){
        //Correct submit
        loadXmlErrorFile = false;
        loadFile = false;
        inputName.innerHTML = 'Transforming your diagram';
        transformDiagram(file);
    } else {
        //Incorrect submit
        alert('There is not a diagram selected');
    }
});

// Function to make the HTTP Post request to the Chowlk API
function transformDiagram(file){
    loadTransformedDiagram = false;
    //const uri = 'https://chowlk.linkeddata.es/api';
    const uri = 'http://localhost:5000/api';
    // Create an HTTP request
    const xhr = new XMLHttpRequest();
    // Specify how the data is going to be sent in the request
    const fd = new FormData();
    // Set the type of the request (Post)
    xhr.open('POST', uri);
    // When the response is received the following function is going to be executed
    xhr.onreadystatechange = function(){
        if(xhr.readyState == 4 && xhr.status == 200){
            //Diagram transformed
            response = JSON.parse(xhr.responseText);
            
            errorReport.style.display = 'none';
            warningReport.style.display = 'none';
            xmlErrors.style.display = 'none';
            newNamespaces.style.display = 'none';
            
            inputName.style.display = 'none';
            responseText.style.display = 'block';
            responseText.innerText = response['ttl_data'];
            loadTransformedDiagram = true;

            var errors_keys = Object.keys(response['errors']);
            var warnings_keys = Object.keys(response['warnings']);
            var namespaces_keys = Object.keys(response['new_namespaces']);

            //xml file with highlight errors
            loadXmlErrorFile = response['xml_error_generated'];
        
            if (warnings_keys.length > 0){
                warningReport.style.display = 'block';

                baseBody.innerHTML = '';
                ontologyUriBody.innerHTML = '';
                restrictionsWBody.innerHTML = '';
                deprecatedBody.innerHTML = '';
                
                baseItem.style.display = 'none';
                ontologyUriItem.style.displey = 'none';
                restrictionsWItem.style.display = 'none';
                deprecatedItem.style.display = 'none';

                warnings_keys.forEach((key) => classifyWarning(key, response['warnings'][key]));
            }

            if (errors_keys.length > 0){
                //The diagram has error that is neccesary to show to the user
                errorReport.style.display = 'block';
                if (loadXmlErrorFile){
                    xmlErrors.style.display = 'block';
                }

                conceptsBody.innerHTML = '';
                arrowsBody.innerHTML = '';
                ellipsesBody.innerHTML = '';
                attributesBody.innerHTML = '';
                namespacesBody.innerHTML = '';
                metadataBody.innerHTML = '';
                rhombusesBody.innerHTML = '';
                individualBody.innerHTML = '';
                hexagonsBody.innerHTML = '';
                cardinalityRestrictionsBody.innerHTML = '';
                intersectionOfBody.innerHTML = '';
                oneOfBody.innerHTML = '';
                complementOfBody.innerHTML = '';
                unionOfBody.innerHTML = '';
                relationBody.innerHTML = '';
                annotationPropertyBody.innerHTML = '';
                baseErrorBody.innerHTML = '';
                syntaxBody.innerHTML = '';
                serverErrorBody.innerHTML = '';

                conceptsItem.style.display = 'none';
                arrowsItem.style.display = 'none';
                ellipsesItem.style.display = 'none';
                attributesItem.style.display = 'none';
                namespacesItem.style.display = 'none';
                metadataItem.style.display = 'none';
                rhombusesItem.style.display = 'none';
                individualItem.style.display = 'none';
                hexagonsItem.style.display = 'none';
                cardinalityRestrictionsItem.style.display = 'none';
                intersectionOfItem.style.display = 'none';
                oneOfItem.style.display = 'none';
                complementOfItem.style.display = 'none';
                unionOfItem.style.display = 'none';
                relationItem.style.display = 'none';
                annotationPropertyItem.style.display = 'none';
                baseErrorItem.style.display = 'none';
                syntaxItem.style.display = 'none';
                serverErrorItem.style.display = 'none';
                
                errors_keys.forEach((key) => classifyError(key, response['errors'][key]));
            }

            if (namespaces_keys.length > 0){
                errorReport.style.display = 'block';
                textNamespace.innerHTML = '';
                newNamespaces.style.display = 'block';

                var unorderedList = document.createElement('ul');

                for(let k = 0; k < namespaces_keys.length; k++){
                    prefix = namespaces_keys[k]
                    namespace = response['new_namespaces'][prefix]

                    var listBullet = document.createElement('li');
                    listBullet.innerHTML = '<b>' + prefix + ': </b>' + namespace;
                    unorderedList.appendChild(listBullet);
                }

                textNamespace.appendChild(unorderedList);
            }
        }    
    }
    // Append the file (diagram)
    fd.append('data', file);
    // Send the HTTP Post request
    xhr.send(fd);
}

// Function to display the warning text in their relevant accordion
function classifyWarning(key, value){
    if (key == 'Base'){
        showError(baseItem, baseBody, value);
    }
    else if (key == 'Ontology'){
        showError(ontologyUriItem, ontologyUriBody, value);
    }
    else if (key == 'Restrictions'){
        showError(restrictionsWItem, restrictionsWBody, value);
    }
    else if (key == 'Deprecated'){
        showError(deprecatedItem, deprecatedBody, value);
    }
}

// Function to display the error text in their relevant accordion
function classifyError(key, value){
    switch(key){
        case 'Concepts':
            showError(conceptsItem, conceptsBody, value);
            break;
        case 'Arrows':
            showError(arrowsItem, arrowsBody, value);
            break;
        case 'Ellipses':
            showError(ellipsesItem, ellipsesBody, value);
            break;
        case 'Attributes':
            showError(attributesItem, attributesBody, value);
            break;
        case 'Namespaces':
            showError(namespacesItem, namespacesBody, value);
            break;
        case 'Metadata':
            showError(metadataItem, metadataBody, value);
            break;
        case 'Rhombuses':
            showError(rhombusesItem, rhombusesBody, value);
            break;
        case 'Individual':
            showError(individualItem, individualBody, value);
            break;
        case 'Hexagons':
            showError(hexagonsItem, hexagonsBody, value);
            break;
        case 'Cardinality-Restrictions':
            showError(cardinalityRestrictionsItem, cardinalityRestrictionsBody, value);
            break;
        case 'intersectionOf':
            showError(intersectionOfItem, intersectionOfBody, value);
            break;
        case 'oneOf':
            showError(oneOfItem, oneOfBody, value);
            break;
        case 'complementOf':
            showError(complementOfItem, complementOfBody, value);
            break;
        case 'unionOf':
            showError(unionOfItem, unionOfBody, value);
            break;
        case 'Relations':
            showError(relationItem, relationBody, value);
            break;
        case 'Annotation Properties':
            showError(annotationPropertyItem, annotationPropertyBody, value);
            break;
        case 'Base':
            showError(baseErrorItem, baseErrorBody, value);
            break;
        case 'Syntax':
            showSimpleError(syntaxItem, syntaxBody, value);
            break;
        case 'Server Error':
            showSimpleError(serverErrorItem, serverErrorBody, value);
            break;
    }
}

function showError(item, body, errors){
    var unorderedList = document.createElement('ul');
    item.style.display = 'block';

    for(let j = 0; j < errors.length; j++){
        var listBullet = document.createElement('li');
        text = '';
        if(errors[j]['value']){
            text = '<b>Value:</b> '  + errors[j]['value'].replaceAll('<','&lt;').replaceAll('>','&gt;');
        }
        if(errors[j]['message']){
            if(text != ''){
                text += ', ';
            }
            text += '<b>Problem:</b> ' + errors[j]['message'];
        }
        if(errors[j]['shape_id']){
            if(text != ''){
                text += ', ';
            }
            text += '<b>Shape id:</b> ' + errors[j]['shape_id'];
        }
        //listBullet.innerHTML = '<b>Value:</b> '  + errors[j]['value'] + ', <b>Problem:</b> ' + errors[j]['message'] + ', <b>Shape id:</b> ' + errors[j]['shape_id'];
        listBullet.innerHTML = text;
        unorderedList.appendChild(listBullet);
    }
    body.appendChild(unorderedList);
}

function showSimpleError(item, body, errors){
    var unorderedList = document.createElement('ul');
    item.style.display = 'block';

    var listBullet = document.createElement('li');
    listBullet.innerHTML = '<b>Message:</b> '  + errors['message'];
    unorderedList.appendChild(listBullet);
    body.appendChild(unorderedList);
}

//Click event handler for the button 'download' in order to download the ttl file
//If there is not a transform diagram loaded => warn the user
//If there is a transform diagram loaded => download it
downloadButton.addEventListener('click', ()=>{
    if(loadTransformedDiagram){
        downloadFile('ontology.ttl', response['ttl_data']);
    } else{
        alert('There is not loaded a transform diagram');
    }
});

//Click event handler for the button 'download' in order to download the xml error file
//If there is not a xml error file loaded => warn the user
//If there is a xml error file loaded => download it
downloadButtonXmlErrorFile.addEventListener('click', ()=>{
    if(loadXmlErrorFile){
        downloadFile('ontology.xml', response['xml_error_file']);
    } else{
        alert('There is not loaded an xml error file');
    }
});

// Function to download a file
function downloadFile(filename, text){
    var element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', filename);

    element.style.display = 'none';
    document.body.appendChild(element);

    element.click();

    document.body.removeChild(element);
}
