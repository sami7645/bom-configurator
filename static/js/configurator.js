// BOM Configurator JavaScript

let currentStep = 1;
let configurationData = {};
let gnxArticles = [];

$(document).ready(function() {
    // Initialize form validation
    initializeValidation();
    
    // Event handlers
    $('#schachttyp, #hvbSize').on('change', updateSondenOptions);
    $('#anschlussart').on('change', updateSondenabstandOptions);
    $('#sondenDurchmesser').on('change', updateSondenanzahlRange);
    $('#schachttyp').on('change', checkGNXChamber);
    $('#hvbSize').on('change', loadGNXArticles);
});

function initializeValidation() {
    // Add validation classes on input
    $('.form-control, .form-select').on('input change', function() {
        validateField(this);
    });
}

function validateField(field) {
    const $field = $(field);
    const value = $field.val();
    
    $field.removeClass('is-valid is-invalid');
    
    if ($field.prop('required') && !value) {
        $field.addClass('is-invalid');
        return false;
    } else if (value) {
        $field.addClass('is-valid');
        return true;
    }
    
    return true;
}

function validateStep(step) {
    let isValid = true;
    
    $(`#config-step-${step} .form-control[required], #config-step-${step} .form-select[required]`).each(function() {
        if (!validateField(this)) {
            isValid = false;
        }
    });
    
    return isValid;
}

function nextStep(step) {
    if (!validateStep(currentStep)) {
        BOMConfigurator.showAlert('Bitte füllen Sie alle Pflichtfelder aus.', 'warning');
        return;
    }
    
    // Hide current step
    $(`#config-step-${currentStep}`).addClass('d-none');
    
    // Update step indicators
    $(`#step-${currentStep}`).removeClass('active').addClass('completed');
    $(`#step-${step}`).addClass('active');
    
    // Show next step
    $(`#config-step-${step}`).removeClass('d-none').addClass('fade-in');
    
    currentStep = step;
    
    // Special handling for step 4 (configuration check)
    if (step === 4) {
        checkConfiguration();
    }
    
    // Scroll to top
    $('html, body').animate({ scrollTop: 0 }, 500);
}

function previousStep(step) {
    // Hide current step
    $(`#config-step-${currentStep}`).addClass('d-none');
    
    // Update step indicators
    $(`#step-${currentStep}`).removeClass('active');
    $(`#step-${step}`).removeClass('completed').addClass('active');
    
    // Show previous step
    $(`#config-step-${step}`).removeClass('d-none').addClass('fade-in');
    
    currentStep = step;
    
    // Scroll to top
    $('html, body').animate({ scrollTop: 0 }, 500);
}

function updateSondenOptions() {
    // Add a small delay to ensure dropdown values are properly updated
    setTimeout(() => {
        const schachttyp = $('#schachttyp').val();
        const hvbSize = $('#hvbSize').val();
        
        console.log('updateSondenOptions called:', { schachttyp, hvbSize });
        console.log('updateSondenOptions - Schachttyp selected option:', $('#schachttyp option:selected').text());
        console.log('updateSondenOptions - HVB selected option:', $('#hvbSize option:selected').text());
        
        // Double-check the values by re-reading them
        const schachttypCheck = document.getElementById('schachttyp').value;
        const hvbSizeCheck = document.getElementById('hvbSize').value;
        console.log('Double-check values:', { schachttypCheck, hvbSizeCheck });
        
        // Use the double-checked values
        const finalSchachttyp = schachttypCheck || schachttyp;
        const finalHvbSize = hvbSizeCheck || hvbSize;
        
        if (!finalSchachttyp || !finalHvbSize) {
            console.log('Missing schachttyp or hvbSize, showing placeholder');
            $('#sondenDurchmesser').html('<option value="">Erst Schachttyp und HVB wählen...</option>');
            return;
        }
        
        console.log('Final values being sent:', { finalSchachttyp, finalHvbSize });
        
        performSondenOptionsRequest(finalSchachttyp, finalHvbSize);
    }, 100); // 100ms delay to ensure DOM is updated
}

function performSondenOptionsRequest(schachttyp, hvbSize) {
    console.log('Making AJAX request to /api/sonden-options/');
    
    $.ajax({
        url: '/api/sonden-options/',
        method: 'POST',
        data: JSON.stringify({
            schachttyp: schachttyp,
            hvb_size: hvbSize
        }),
        contentType: 'application/json',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        success: function(data) {
            console.log('API response received:', data);
            console.log('Number of sonden_options:', data.sonden_options ? data.sonden_options.length : 0);
            
            // Log debug info if available
            if (data.debug) {
                console.log('API Debug Info:', data.debug);
                console.log('Received values:', data.debug.received);
                console.log('Result count:', data.debug.count);
            }
            
            let options = '<option value="">Bitte wählen...</option>';
            
            if (data.sonden_options && data.sonden_options.length > 0) {
                data.sonden_options.forEach(function(option) {
                    options += `<option value="${option.durchmesser_sonde}" 
                               data-min="${option.sondenanzahl_min}" 
                               data-max="${option.sondenanzahl_max}">
                               ${option.durchmesser_sonde}mm - ${option.artikelbezeichnung}
                               </option>`;
                });
                console.log('Generated options HTML:', options);
            } else {
                console.log('No sonden_options found in response');
                if (data.error) {
                    console.error('API Error:', data.error);
                    console.error('Received values:', data.received);
                    options += `<option value="">Fehler: ${data.error}</option>`;
                } else {
                    options += '<option value="">Keine Optionen verfügbar</option>';
                    console.warn('No options returned. Check server logs for details.');
                }
            }
            
            $('#sondenDurchmesser').html(options);
            console.log('Updated dropdown HTML');
        },
        error: function(xhr, status, error) {
            console.error('AJAX error:', { xhr, status, error });
            console.error('Response text:', xhr.responseText);
            BOMConfigurator.showAlert('Fehler beim Laden der Sonden-Optionen.', 'danger');
        }
    });
}

function updateSondenabstandOptions() {
    const anschlussart = $('#anschlussart').val();
    
    if (!anschlussart) {
        $('#sondenabstand').html('<option value="">Erst Anschlussart wählen...</option>');
        return;
    }
    
    $.ajax({
        url: '/api/sondenabstand-options/',
        method: 'POST',
        data: JSON.stringify({
            anschlussart: anschlussart
        }),
        contentType: 'application/json',
        success: function(data) {
            let options = '<option value="">Bitte wählen...</option>';
            
            data.abstand_options.forEach(function(option) {
                const hinweis = option.hinweis ? ` (${option.hinweis})` : '';
                options += `<option value="${option.sondenabstand}" 
                           data-zuschlag-links="${option.zuschlag_links}" 
                           data-zuschlag-rechts="${option.zuschlag_rechts}">
                           ${option.sondenabstand}mm${hinweis}
                           </option>`;
            });
            
            $('#sondenabstand').html(options);
        },
        error: function() {
            BOMConfigurator.showAlert('Fehler beim Laden der Sondenabstand-Optionen.', 'danger');
        }
    });
}

function updateSondenanzahlRange() {
    const selectedOption = $('#sondenDurchmesser option:selected');
    const min = selectedOption.data('min');
    const max = selectedOption.data('max');
    
    if (min && max) {
        $('#sondenanzahl').attr('min', min).attr('max', max);
        $('#sondenanzahlRange').text(`Erlaubter Bereich: ${min} - ${max} Sonden`);
    } else {
        $('#sondenanzahlRange').text('');
    }
}

function checkGNXChamber() {
    const schachttyp = $('#schachttyp').val();
    
    if (['GN X1', 'GN X2', 'GN X3', 'GN X4'].includes(schachttyp)) {
        $('#gnxChamberSection').removeClass('d-none');
        loadGNXArticles();
    } else {
        $('#gnxChamberSection').addClass('d-none');
    }
}

function loadGNXArticles() {
    const schachttyp = $('#schachttyp').val();
    const hvbSize = $('#hvbSize').val();
    
    if (!['GN X1', 'GN X2', 'GN X3', 'GN X4'].includes(schachttyp) || !hvbSize) {
        return;
    }
    
    $.ajax({
        url: '/api/gnx-chamber-articles/',
        method: 'POST',
        data: JSON.stringify({
            hvb_size: hvbSize
        }),
        contentType: 'application/json',
        success: function(data) {
            gnxArticles = data.articles;
            renderGNXArticles();
        },
        error: function() {
            BOMConfigurator.showAlert('Fehler beim Laden der GN X Artikel.', 'danger');
        }
    });
}

function renderGNXArticles() {
    let html = '';
    
    gnxArticles.forEach(function(article, index) {
        html += `
            <div class="gnx-article-item">
                <div>
                    <strong>${article.artikelnummer}</strong><br>
                    <small class="text-muted">${article.artikelbezeichnung}</small>
                </div>
                <div>
                    <input type="number" class="form-control" style="width: 100px;" 
                           id="gnx-quantity-${article.id}" 
                           value="1" min="0" step="0.001"
                           ${article.is_automatic ? 'readonly' : ''}>
                </div>
            </div>
        `;
    });
    
    $('#gnxArticlesList').html(html);
}

function checkConfiguration() {
    // Collect form data
    configurationData = {
        configuration_name: $('#configName').val(),
        schachttyp: $('#schachttyp').val(),
        hvb_size: $('#hvbSize').val(),
        sonden_durchmesser: $('#sondenDurchmesser').val(),
        sondenanzahl: $('#sondenanzahl').val(),
        sondenabstand: $('#sondenabstand').val(),
        anschlussart: $('#anschlussart').val(),
        kugelhahn_type: $('#kugelhahnType').val(),
        dfm_type: $('#dfmType').val(),
        zuschlag_links: $('#zuschlagLinks').val(),
        zuschlag_rechts: $('#zuschlagRechts').val()
    };
    
    // Show configuration summary
    showConfigurationSummary();
    
    // Check for existing configurations
    $.ajax({
        url: '/api/check-configuration/',
        method: 'POST',
        data: JSON.stringify(configurationData),
        contentType: 'application/json',
        success: function(data) {
            $('#configurationCheck').addClass('d-none');
            $('#configurationSummary').removeClass('d-none');
            $('#articleNumberSection').removeClass('d-none');
            
            showArticleNumberStatus(data);
            $('#generateBomBtn').prop('disabled', false);
        },
        error: function() {
            BOMConfigurator.showAlert('Fehler beim Prüfen der Konfiguration.', 'danger');
        }
    });
}

function showConfigurationSummary() {
    const summaryData = [
        ['Konfigurationsname', configurationData.configuration_name],
        ['Schachttyp', configurationData.schachttyp],
        ['HVB-Größe', `${configurationData.hvb_size}mm`],
        ['Sonden-Durchmesser', `${configurationData.sonden_durchmesser}mm`],
        ['Anzahl Sonden', configurationData.sondenanzahl],
        ['Sondenabstand', `${configurationData.sondenabstand}mm`],
        ['Anschlussart', configurationData.anschlussart],
        ['Kugelhahn-Typ', configurationData.kugelhahn_type || 'Nicht ausgewählt'],
        ['DFM-Typ', configurationData.dfm_type || 'Nicht ausgewählt']
    ];
    
    let html = '';
    summaryData.forEach(function(row) {
        html += `<tr><td><strong>${row[0]}:</strong></td><td>${row[1]}</td></tr>`;
    });
    
    $('#configSummaryTable').html(html);
}

function showArticleNumberStatus(data) {
    let html = '';
    let statusClass = '';
    let statusText = '';
    
    if (data.exists) {
        if (data.type === 'full_configuration') {
            statusClass = 'status-existing';
            statusText = 'Bestehende Konfiguration';
            html = `
                <div class="alert alert-success">
                    <h6><i class="fas fa-check-circle me-2"></i>Konfiguration bereits vorhanden</h6>
                    <p>${data.message}</p>
                    <p><strong>Artikelnummer:</strong> <code>${data.article_number}</code></p>
                </div>
            `;
            configurationData.full_article_number = data.article_number;
            configurationData.is_existing_configuration = true;
            
        } else if (data.type === 'mother_article') {
            statusClass = 'status-mother';
            statusText = 'Mutterartikel vorhanden';
            html = `
                <div class="alert alert-warning">
                    <h6><i class="fas fa-exclamation-triangle me-2"></i>Mutterartikel gefunden</h6>
                    <p>${data.message}</p>
                    <div class="mb-3">
                        <label class="form-label">Kindartikelnummer:</label>
                        <input type="text" class="form-control" id="childArticleNumber" 
                               value="${data.suggested_child_number}" required>
                    </div>
                </div>
            `;
            configurationData.mother_article_number = data.mother_article_number;
            configurationData.is_existing_mother_article = true;
        }
    } else {
        statusClass = 'status-new';
        statusText = 'Neue Konfiguration';
        html = `
            <div class="alert alert-info">
                <h6><i class="fas fa-plus-circle me-2"></i>Neue Konfiguration</h6>
                <p>${data.message}</p>
                <div class="mb-3">
                    <label class="form-label">Neue Artikelnummer:</label>
                    <input type="text" class="form-control" id="newArticleNumber" 
                           placeholder="z.B. 1000089-001" required>
                </div>
            </div>
        `;
    }
    
    html += `<div class="status-badge ${statusClass}">${statusText}</div>`;
    $('#articleNumberContent').html(html);
}

function generateBOM() {
    const generateBtn = $('#generateBomBtn');
    BOMConfigurator.showLoading(generateBtn);
    
    // Update configuration data with article numbers
    if ($('#childArticleNumber').length) {
        configurationData.child_article_number = $('#childArticleNumber').val();
    }
    if ($('#newArticleNumber').length) {
        configurationData.full_article_number = $('#newArticleNumber').val();
    }
    
    // Add GN X articles if applicable
    if (gnxArticles.length > 0) {
        configurationData.gnx_articles = [];
        gnxArticles.forEach(function(article) {
            const quantity = $(`#gnx-quantity-${article.id}`).val();
            if (quantity && parseFloat(quantity) > 0) {
                configurationData.gnx_articles.push({
                    id: article.id,
                    quantity: parseFloat(quantity)
                });
            }
        });
    }
    
    $.ajax({
        url: '/api/generate-bom/',
        method: 'POST',
        data: JSON.stringify(configurationData),
        contentType: 'application/json',
        success: function(data) {
            BOMConfigurator.hideLoading(generateBtn);
            
            if (data.success) {
                nextStep(5);
                showBOMResult(data);
                BOMConfigurator.showAlert('BOM erfolgreich generiert!', 'success');
            } else {
                BOMConfigurator.showAlert(data.message || 'Fehler beim Generieren der BOM.', 'danger');
            }
        },
        error: function() {
            BOMConfigurator.hideLoading(generateBtn);
            BOMConfigurator.showAlert('Fehler beim Generieren der BOM.', 'danger');
        }
    });
}

function showBOMResult(data) {
    let html = `
        <div class="alert alert-success">
            <h6><i class="fas fa-check-circle me-2"></i>BOM erfolgreich generiert</h6>
            <p><strong>Konfiguration:</strong> ${configurationData.configuration_name}</p>
            <p><strong>Artikelnummer:</strong> <code>${data.article_number}</code></p>
        </div>
        
        <div class="bom-table">
            <table class="table table-striped mb-0">
                <thead>
                    <tr>
                        <th>Pos.</th>
                        <th>Artikelnummer</th>
                        <th>Artikelbezeichnung</th>
                        <th>Menge</th>
                        <th>Quelle</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.bom_items.forEach(function(item, index) {
        html += `
            <tr>
                <td>${index + 1}</td>
                <td><code>${item.artikelnummer}</code></td>
                <td>${item.artikelbezeichnung}</td>
                <td>${BOMConfigurator.formatNumber(item.menge, 3)}</td>
                <td><span class="badge bg-secondary">${item.source}</span></td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        
        <div class="text-center mt-4">
            <a href="/configuration/${data.configuration_id}/" class="btn btn-primary me-2">
                <i class="fas fa-eye me-2"></i>Konfiguration anzeigen
            </a>
            <button type="button" class="btn btn-outline-primary me-2" onclick="printBOM()">
                <i class="fas fa-print me-2"></i>BOM drucken
            </button>
            <a href="/configurator/" class="btn btn-outline-secondary">
                <i class="fas fa-plus me-2"></i>Neue Konfiguration
            </a>
        </div>
    `;
    
    $('#bomResult').html(html);
}

function printBOM() {
    window.print();
}

// Manual test function for debugging
function testSondenAPI() {
    const schachttyp = $('#schachttyp').val();
    const hvbSize = $('#hvbSize').val();
    
    console.log('=== MANUAL API TEST ===');
    console.log('Schachttyp value:', schachttyp);
    console.log('HVB Size value:', hvbSize);
    console.log('Schachttyp type:', typeof schachttyp);
    console.log('HVB Size type:', typeof hvbSize);
    
    // Debug dropdown states
    console.log('Schachttyp dropdown HTML:', $('#schachttyp')[0].outerHTML);
    console.log('HVB dropdown HTML:', $('#hvbSize')[0].outerHTML);
    console.log('Schachttyp selected index:', $('#schachttyp')[0].selectedIndex);
    console.log('HVB selected index:', $('#hvbSize')[0].selectedIndex);
    console.log('Schachttyp selected option:', $('#schachttyp option:selected').text());
    console.log('HVB selected option:', $('#hvbSize option:selected').text());
    
    // Double-check with vanilla JavaScript
    const schachttypCheck = document.getElementById('schachttyp').value;
    const hvbSizeCheck = document.getElementById('hvbSize').value;
    console.log('Vanilla JS values:', { schachttypCheck, hvbSizeCheck });
    
    // Use the most reliable values
    const finalSchachttyp = schachttypCheck || schachttyp;
    const finalHvbSize = hvbSizeCheck || hvbSize;
    
    console.log('Final values for API:', { finalSchachttyp, finalHvbSize });
    
    if (!finalSchachttyp || !finalHvbSize) {
        alert('Please select both Schachttyp and HVB-Größe first!');
        return;
    }
    
    const requestData = {
        schachttyp: finalSchachttyp,
        hvb_size: finalHvbSize
    };
    
    console.log('Request data:', requestData);
    console.log('Request JSON:', JSON.stringify(requestData));
    
    $.ajax({
        url: '/api/sonden-options/',
        method: 'POST',
        data: JSON.stringify(requestData),
        contentType: 'application/json',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        success: function(data) {
            console.log('=== API SUCCESS ===');
            console.log('Full response:', data);
            console.log('Options count:', data.sonden_options ? data.sonden_options.length : 0);
            
            if (data.sonden_options && data.sonden_options.length > 0) {
                console.log('Options received:');
                data.sonden_options.forEach((option, index) => {
                    console.log(`  ${index + 1}. ${option.durchmesser_sonde}mm - ${option.artikelbezeichnung}`);
                });
                alert(`SUCCESS! Received ${data.sonden_options.length} probe options. Check console for details.`);
            } else {
                console.log('No options in response');
                alert('API returned empty options list. Check console for details.');
            }
        },
        error: function(xhr, status, error) {
            console.log('=== API ERROR ===');
            console.error('XHR:', xhr);
            console.error('Status:', status);
            console.error('Error:', error);
            console.error('Response text:', xhr.responseText);
            alert(`API Error: ${error}. Check console for details.`);
        }
    });
}

// Export functions for global use
window.nextStep = nextStep;
window.previousStep = previousStep;
window.generateBOM = generateBOM;
window.printBOM = printBOM;
window.testSondenAPI = testSondenAPI;
