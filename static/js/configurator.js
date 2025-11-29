// BOM Configurator JavaScript

let currentStep = 1;
let configurationData = {};
let gnxArticles = [];

$(document).ready(function() {
    // Initialize form validation
    initializeValidation();
    
    // Initialize dropdowns
    $('#sondenDurchmesser').html('<option value="">Erst Schachttyp und HVB wählen...</option>');
    $('#sondenabstand').html('<option value="">Erst Anschlussart wählen...</option>');
    
    // Event handlers
    $('#schachttyp, #hvbSize').on('change', function() {
        updateSondenOptions();
    });
    $('#anschlussart').on('change', updateSondenabstandOptions);
    $('#sondenDurchmesser').on('change', updateSondenanzahlRange);
    $('#schachttyp').on('change', checkGNXChamber);
    $('#hvbSize').on('change', loadGNXArticles);
    $('#dfmCategory').on('change', updateDFMOptions);
    
    // Length calculation display updates
    const lengthInputs = '#sondenanzahl, #sondenabstand, #zuschlagLinks, #zuschlagRechts, #bauform, #anschlussart';
    $(lengthInputs).on('input change', updateLengthDisplays);
    $('#hvbSize').on('change', updateLengthDisplays);
    
    // Alternative calculation inputs
    $('#sondenabstandAlt, #anschlussartAlt').on('change', updateProbeDistanceDisplay);
    
    // When alternative dropdown is clicked/focused, ensure it has options
    $('#sondenabstandAlt').on('focus click', function() {
        console.log('Alternative dropdown focused/clicked - checking if it has options...');
        const altDropdown = $(this);
        const mainDropdown = $('#sondenabstand');
        
        if (altDropdown.find('option').length <= 1 && mainDropdown.find('option').length > 1) {
            console.log('Alternative dropdown is empty but main has options - syncing now...');
            syncAlternativeSondenabstandDropdown();
        }
    });
    
    // Sync sondenabstandAlt with main sondenabstand
    // This ensures alternative dropdown ALWAYS has the same options
    $('#sondenabstand').on('change DOMSubtreeModified', function() {
        const val = $(this).val();
        // Always ensure alternative dropdown has the same options as main dropdown
        console.log('Main sondenabstand changed, syncing alternative dropdown...');
        syncAlternativeSondenabstandDropdown();
        updateLengthDisplays();
    });
    
    // Also watch for when options are added to main dropdown
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.target.id === 'sondenabstand') {
                console.log('Main sondenabstand options changed, syncing...');
                syncAlternativeSondenabstandDropdown();
            }
        });
    });
    
    // Start observing when main dropdown exists
    setTimeout(function() {
        const mainDropdown = document.getElementById('sondenabstand');
        if (mainDropdown) {
            observer.observe(mainDropdown, { childList: true, subtree: true });
            console.log('Started observing main sondenabstand dropdown for changes');
        }
    }, 1000);
    
    // Sync anschlussartAlt with main anschlussart
    $('#anschlussart').on('change', function() {
        const val = $(this).val();
        $('#anschlussartAlt').val(val);
        // updateSondenabstandOptions will be called by the other handler, which will populate the alternative sondenabstand dropdown
        updateLengthDisplays();
    });
    
    // Initial update
    updateLengthDisplays();
    
    // Watch for when Step 2 becomes visible and ensure alternative dropdown is populated
    const step2Observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            const step2Element = document.getElementById('config-step-2');
            if (step2Element && !step2Element.classList.contains('d-none')) {
                // Step 2 is visible, check if alternative dropdown needs options
                setTimeout(function() {
                    const mainDropdown = document.getElementById('sondenabstand');
                    const altDropdown = document.getElementById('sondenabstandAlt');
                    
                    if (mainDropdown && altDropdown && mainDropdown.options.length > 1 && altDropdown.options.length <= 1) {
                        console.log('Step 2 visible - populating alternative dropdown from main dropdown');
                        altDropdown.innerHTML = mainDropdown.innerHTML;
                        if (mainDropdown.value) {
                            altDropdown.value = mainDropdown.value;
                        }
                    }
                }, 100);
            }
        });
    });
    
    // Start observing the step container
    setTimeout(function() {
        const stepContainer = document.querySelector('.container-fluid');
        if (stepContainer) {
            step2Observer.observe(stepContainer, { 
                childList: true, 
                subtree: true, 
                attributes: true,
                attributeFilter: ['class']
            });
        }
    }, 500);
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
    
    // Show next step FIRST so elements are in DOM
    $(`#config-step-${step}`).removeClass('d-none').addClass('fade-in');
    
    currentStep = step;
    
    // Ensure sonden options are loaded when entering step 2
    if (step === 2) {
        // Wait a bit for DOM to be ready
        setTimeout(function() {
            console.log('=== Entering Step 2 ===');
            const altDropdownExists = $('#sondenabstandAlt').length > 0;
            const altDropdownDomExists = document.getElementById('sondenabstandAlt') !== null;
            console.log('sondenabstandAlt (jQuery) exists:', altDropdownExists);
            console.log('sondenabstandAlt (DOM) exists:', altDropdownDomExists);
            
            updateSondenOptions();
            // Sync anschlussartAlt immediately
            $('#anschlussartAlt').val($('#anschlussart').val());
            
            // If anschlussart is already selected, make sure sondenabstand options are loaded
            if ($('#anschlussart').val()) {
                // Check if main dropdown already has options (from previous step)
                const mainOptionCount = $('#sondenabstand option').length;
                console.log('Main dropdown has', mainOptionCount, 'options');
                
                if (mainOptionCount > 1) {
                    // Copy existing options to alternative dropdown immediately
                    console.log('Syncing from existing main dropdown options...');
                    syncAlternativeSondenabstandDropdown();
                }
                
                // Also call API to ensure we have the latest options (this will also sync)
                console.log('Calling updateSondenabstandOptions...');
                updateSondenabstandOptions();
            } else {
                // If no anschlussart, clear alternative dropdown
                if (altDropdownExists) {
                    $('#sondenabstandAlt').html('<option value="">Erst Anschlussart wählen...</option>');
                }
                if (altDropdownDomExists) {
                    document.getElementById('sondenabstandAlt').innerHTML = '<option value="">Erst Anschlussart wählen...</option>';
                }
            }
            
            // Update displays after a delay to ensure dropdowns are populated
            setTimeout(function() {
                // Final sync check to ensure alternative dropdown is populated
                console.log('=== Final sync check ===');
                const synced = syncAlternativeSondenabstandDropdown();
                if (!synced) {
                    console.warn('Sync failed, retrying in 200ms...');
                    setTimeout(function() {
                        syncAlternativeSondenabstandDropdown();
                    }, 200);
                }
                updateLengthDisplays();
            }, 1000);
        }, 300);
    }
    
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
    
    // Show previous step FIRST so elements are in DOM
    $(`#config-step-${step}`).removeClass('d-none').addClass('fade-in');
    
    currentStep = step;
    
    // Ensure sonden options are loaded when going back to step 2
    if (step === 2) {
        // Wait a bit for DOM to be ready
        setTimeout(function() {
            console.log('Returning to Step 2 - checking dropdowns...');
            console.log('sondenabstandAlt exists:', $('#sondenabstandAlt').length > 0);
            
            updateSondenOptions();
            // Sync anschlussartAlt immediately
            $('#anschlussartAlt').val($('#anschlussart').val());
            // If anschlussart is already selected, make sure sondenabstand options are loaded
            if ($('#anschlussart').val()) {
                // Check if main dropdown already has options (from previous step)
                if ($('#sondenabstand option').length > 1) {
                    // Copy existing options to alternative dropdown immediately
                    console.log('Syncing from existing main dropdown options...');
                    syncAlternativeSondenabstandDropdown();
                }
                // Also call API to ensure we have the latest options (this will also sync)
                console.log('Calling updateSondenabstandOptions...');
                updateSondenabstandOptions();
            } else {
                // If no anschlussart, clear alternative dropdown
                $('#sondenabstandAlt').html('<option value="">Erst Anschlussart wählen...</option>');
            }
            // Update displays after a delay to ensure dropdowns are populated
            setTimeout(function() {
                // Final sync check to ensure alternative dropdown is populated
                console.log('=== Final sync check ===');
                const synced = syncAlternativeSondenabstandDropdown();
                if (!synced) {
                    console.warn('Sync failed, retrying in 200ms...');
                    setTimeout(function() {
                        syncAlternativeSondenabstandDropdown();
                    }, 200);
                }
                updateLengthDisplays();
            }, 800);
            
            // Also try to sync immediately when Step 2 becomes visible
            // Use a MutationObserver to detect when Step 2 is shown
            setTimeout(function() {
                const step2Element = document.getElementById('config-step-2');
                if (step2Element && !step2Element.classList.contains('d-none')) {
                    console.log('Step 2 is visible, forcing sync...');
                    syncAlternativeSondenabstandDropdown();
                }
            }, 300);
        }, 200);
    }
    
    // Scroll to top
    $('html, body').animate({ scrollTop: 0 }, 500);
}

function updateSondenOptions() {
    // Get values directly from DOM elements (most reliable)
    const schachttyp = $('#schachttyp').val() || '';
    const hvbSize = $('#hvbSize').val() || '';
    
    console.log('updateSondenOptions called - schachttyp:', schachttyp, 'hvbSize:', hvbSize);
    
    if (!schachttyp || !hvbSize) {
        $('#sondenDurchmesser').html('<option value="">Erst Schachttyp und HVB wählen...</option>');
        return;
    }
    
    // Clean values
    const cleanSchachttyp = schachttyp.trim();
    let cleanHvbSize = hvbSize.trim();
    // Remove 'mm' suffix if present
    if (cleanHvbSize.toLowerCase().endsWith('mm')) {
        cleanHvbSize = cleanHvbSize.slice(0, -2).trim();
    }
    
    // Show loading state
    $('#sondenDurchmesser').html('<option value="">Lade Optionen...</option>');
    
    // Make AJAX request
    $.ajax({
        url: '/api/sonden-options/',
        method: 'POST',
        cache: false,
        data: JSON.stringify({
            schachttyp: cleanSchachttyp,
            hvb_size: cleanHvbSize
        }),
        contentType: 'application/json',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        success: function(data) {
            console.log('API success - options count:', data.sonden_options ? data.sonden_options.length : 0);
            
            let options = '<option value="">Bitte wählen...</option>';
            
            if (data.sonden_options && data.sonden_options.length > 0) {
                data.sonden_options.forEach(function(option) {
                    options += `<option value="${option.durchmesser_sonde}" 
                               data-min="${option.sondenanzahl_min}" 
                               data-max="${option.sondenanzahl_max}">
                               ${option.durchmesser_sonde}mm - ${option.artikelbezeichnung}
                               </option>`;
                });
            } else {
                options = '<option value="">Keine Optionen verfügbar</option>';
                if (data.error) {
                    console.error('API Error:', data.error);
                }
            }
            
            $('#sondenDurchmesser').html(options);
        },
        error: function(xhr, status, error) {
            console.error('AJAX error:', error, xhr.responseText);
            $('#sondenDurchmesser').html('<option value="">Fehler beim Laden</option>');
            if (typeof BOMConfigurator !== 'undefined' && BOMConfigurator.showAlert) {
                BOMConfigurator.showAlert('Fehler beim Laden der Sonden-Optionen.', 'danger');
            }
        }
    });
}

function syncAlternativeSondenabstandDropdown() {
    // Helper function to sync alternative dropdown with main dropdown
    console.log('=== syncAlternativeSondenabstandDropdown called ===');
    
    // Use native DOM for more reliable access
    const mainDropdownDom = document.getElementById('sondenabstand');
    const altDropdownDom = document.getElementById('sondenabstandAlt');
    
    const mainDropdown = $('#sondenabstand');
    const altDropdown = $('#sondenabstandAlt');
    
    console.log('Main dropdown (jQuery) exists:', mainDropdown.length > 0);
    console.log('Main dropdown (DOM) exists:', mainDropdownDom !== null);
    console.log('Alt dropdown (jQuery) exists:', altDropdown.length > 0);
    console.log('Alt dropdown (DOM) exists:', altDropdownDom !== null);
    
    if (!mainDropdownDom && !mainDropdown.length) {
        console.error('Main dropdown #sondenabstand not found!');
        return false;
    }
    
    if (!altDropdownDom && !altDropdown.length) {
        console.error('Alternative dropdown #sondenabstandAlt not found!');
        return false;
    }
    
    // Get option count from main dropdown
    const mainOptionCount = mainDropdownDom ? mainDropdownDom.options.length : mainDropdown.find('option').length;
    const mainVal = mainDropdownDom ? mainDropdownDom.value : mainDropdown.val();
    
    console.log('Main dropdown options count:', mainOptionCount);
    console.log('Main dropdown current value:', mainVal);
    
    // Check if main dropdown has valid options (more than just placeholder)
    if (mainOptionCount > 1) {
        console.log('Copying options to alternative dropdown...');
        
        // Use native DOM method - more reliable
        if (altDropdownDom && mainDropdownDom) {
            // Clear and rebuild options
            altDropdownDom.innerHTML = '';
            
            // Copy each option
            for (let i = 0; i < mainDropdownDom.options.length; i++) {
                const option = mainDropdownDom.options[i];
                const newOption = document.createElement('option');
                newOption.value = option.value;
                newOption.text = option.text;
                // Copy data attributes if any
                if (option.dataset) {
                    Object.keys(option.dataset).forEach(key => {
                        newOption.setAttribute('data-' + key, option.dataset[key]);
                    });
                }
                altDropdownDom.appendChild(newOption);
            }
            
            console.log('Copied', altDropdownDom.options.length, 'options via DOM method');
            
            // Set the value if main dropdown has a selection
            if (mainVal && mainVal !== '') {
                altDropdownDom.value = mainVal;
                console.log('Set alternative dropdown value to:', mainVal);
            }
            
            // Also try jQuery method as backup
            if (altDropdown.length > 0) {
                altDropdown.html(mainDropdown.html());
                if (mainVal) {
                    altDropdown.val(mainVal);
                }
            }
            
            console.log('=== Sync completed successfully ===');
            return true;
        } else if (altDropdown.length > 0 && mainDropdown.length > 0) {
            // Fallback to jQuery
            altDropdown.html(mainDropdown.html());
            if (mainVal) {
                altDropdown.val(mainVal);
            }
            console.log('=== Sync completed via jQuery ===');
            return true;
        }
    } else {
        console.log('Main dropdown has no valid options to sync (only placeholder)');
        return false;
    }
    
    return false;
}

function updateSondenabstandOptions() {
    const anschlussart = $('#anschlussart').val();
    
    if (!anschlussart) {
        $('#sondenabstand').html('<option value="">Erst Anschlussart wählen...</option>');
        $('#sondenabstandAlt').html('<option value="">Erst Anschlussart wählen...</option>');
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
            let standardOption = null;
            
            if (!data.abstand_options || data.abstand_options.length === 0) {
                $('#sondenabstand').html('<option value="">Keine Optionen verfügbar</option>');
                $('#sondenabstandAlt').html('<option value="">Keine Optionen verfügbar</option>');
                return;
            }
            
            data.abstand_options.forEach(function(option) {
                const hinweis = option.hinweis ? ` (${option.hinweis})` : '';
                const isStandard = option.hinweis && option.hinweis.toLowerCase() === 'standard';
                
                options += `<option value="${option.sondenabstand}" 
                           data-zuschlag-links="${option.zuschlag_links}" 
                           data-zuschlag-rechts="${option.zuschlag_rechts}"
                           ${isStandard ? 'selected' : ''}>
                           ${option.sondenabstand}mm${hinweis}
                           </option>`;
                           
                // Store the standard option for updating zuschläge
                if (isStandard) {
                    standardOption = option;
                }
            });
            
            // Set main dropdown
            $('#sondenabstand').html(options);
            console.log('Main sondenabstand dropdown populated with', data.abstand_options.length, 'options');
            
            // IMMEDIATELY populate the alternative dropdown with the EXACT SAME options
            // Use BOTH jQuery and native DOM to ensure it works
            console.log('=== Populating alternative dropdown ===');
            const altDropdown = $('#sondenabstandAlt');
            const altDropdownDom = document.getElementById('sondenabstandAlt');
            
            console.log('Alternative dropdown (jQuery) found:', altDropdown.length > 0);
            console.log('Alternative dropdown (DOM) found:', altDropdownDom !== null);
            
            if (altDropdown.length > 0 || altDropdownDom !== null) {
                // Try jQuery first
                if (altDropdown.length > 0) {
                    altDropdown.html(options);
                    console.log('Set via jQuery, options count:', altDropdown.find('option').length);
                }
                
                // ALWAYS also use native DOM method as backup
                if (altDropdownDom) {
                    altDropdownDom.innerHTML = options;
                    console.log('Set via DOM, options count:', altDropdownDom.options.length);
                    
                    // Verify it worked
                    if (altDropdownDom.options.length > 0) {
                        console.log('SUCCESS: Alternative dropdown populated via DOM');
                        for (let i = 0; i < altDropdownDom.options.length; i++) {
                            console.log('  Option', i + ':', altDropdownDom.options[i].value, '-', altDropdownDom.options[i].text);
                        }
                    } else {
                        console.error('ERROR: DOM method also failed - dropdown still empty!');
                    }
                } else {
                    console.error('ERROR: Alternative dropdown element not found in DOM!');
                }
                
                // If a standard option was found and selected, update the zuschläge fields
                if (standardOption) {
                    $('#zuschlagLinks').val(standardOption.zuschlag_links);
                    $('#zuschlagRechts').val(standardOption.zuschlag_rechts);
                    // Set both dropdowns to the standard option
                    if (altDropdown.length > 0) {
                        altDropdown.val(standardOption.sondenabstand);
                    }
                    if (altDropdownDom) {
                        altDropdownDom.value = standardOption.sondenabstand;
                    }
                    console.log('Set alternative dropdown to standard option:', standardOption.sondenabstand);
                    // Trigger change event in case there are any listeners
                    $('#sondenabstand').trigger('change');
                } else {
                    // If no standard option, try to preserve current selection or use first non-empty option
                    const currentMainVal = $('#sondenabstand').val();
                    if (currentMainVal) {
                        if (altDropdown.length > 0) {
                            altDropdown.val(currentMainVal);
                        }
                        if (altDropdownDom) {
                            altDropdownDom.value = currentMainVal;
                        }
                        console.log('Set alternative dropdown to current main value:', currentMainVal);
                    } else {
                        // Select first non-empty option if available
                        const firstOption = $('#sondenabstand option:not([value=""])').first();
                        if (firstOption.length > 0) {
                            const firstVal = firstOption.val();
                            if (altDropdown.length > 0) {
                                altDropdown.val(firstVal);
                            }
                            if (altDropdownDom) {
                                altDropdownDom.value = firstVal;
                            }
                            console.log('Set alternative dropdown to first option:', firstVal);
                        }
                    }
                }
            } else {
                console.error('Alternative dropdown #sondenabstandAlt not found in DOM!');
                // Try to find it after a delay (in case Step 2 is being shown)
                setTimeout(function() {
                    const retryAlt = document.getElementById('sondenabstandAlt');
                    if (retryAlt) {
                        console.log('Found alternative dropdown on retry, populating...');
                        retryAlt.innerHTML = options;
                        if (standardOption) {
                            retryAlt.value = standardOption.sondenabstand;
                        }
                    }
                }, 500);
            }
            
            // Update displays
            updateLengthDisplays();
        },
        error: function(xhr, status, error) {
            console.error('Error loading sondenabstand options:', error, xhr.responseText);
            BOMConfigurator.showAlert('Fehler beim Laden der Sondenabstand-Optionen.', 'danger');
            // Try to sync from main dropdown as fallback
            syncAlternativeSondenabstandDropdown();
        }
    });
}

function updateDFMOptions() {
    const category = $('#dfmCategory').val();
    
    if (!category) {
        $('#dfmType').html('<option value="">Erst Kategorie wählen...</option>').prop('disabled', true).val('');
        return;
    }
    
    // Show loading state
    $('#dfmType').html('<option value="">Lade Optionen...</option>').prop('disabled', false);
    
    $.ajax({
        url: '/api/dfm-options/',
        method: 'POST',
        data: JSON.stringify({
            category: category
        }),
        contentType: 'application/json',
        success: function(data) {
            let options = '<option value="">Bitte wählen...</option>';
            
            data.dfm_options.forEach(function(option) {
                options += `<option value="${option}">${option}</option>`;
            });
            
            $('#dfmType').html(options);
        },
        error: function() {
            $('#dfmType').html('<option value="">Fehler beim Laden</option>');
            if (typeof BOMConfigurator !== 'undefined' && BOMConfigurator.showAlert) {
                BOMConfigurator.showAlert('Fehler beim Laden der DFM-Optionen.', 'danger');
            }
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

function updateLengthDisplays() {
    updateHvbLengthDisplay();
    updateProbeDistanceDisplay();
}

function updateHvbLengthDisplay() {
    const sondenanzahlInput = $('#sondenanzahl').val();
    const sondenanzahl = sondenanzahlInput ? parseFloat(sondenanzahlInput) : 0;
    const sondenabstandVal = $('#sondenabstand').val();
    const sondenabstand = sondenabstandVal ? parseFloat(sondenabstandVal) : 0;
    const zuschlagLinks = parseFloat($('#zuschlagLinks').val()) || 0;
    const zuschlagRechts = parseFloat($('#zuschlagRechts').val()) || 0;
    const bauform = $('#bauform').val() || 'I';
    
    // More lenient validation - allow calculation if we have valid numbers, even if sondenanzahl is 1
    if (!sondenanzahlInput || sondenanzahlInput === '' || isNaN(sondenanzahl) || sondenanzahl < 1) {
        $('#hvbLengthDisplay').text('–');
        $('#hvbLengthFormula').text('Bitte Anzahl der Sonden eingeben.');
        return;
    }
    
    if (!sondenabstandVal || sondenabstandVal === '' || isNaN(sondenabstand) || sondenabstand <= 0) {
        $('#hvbLengthDisplay').text('–');
        $('#hvbLengthFormula').text('Bitte den Sondenabstand wählen.');
        return;
    }
    
    let totalMm;
    let formula;
    
    if (bauform === 'U') {
        // U-Form: (sondenanzahl - 1) × 2 × sondenabstand × 2 + zuschläge
        totalMm = (sondenanzahl - 1) * 2 * sondenabstand * 2 + zuschlagLinks + zuschlagRechts;
        formula = `U-Form: (${sondenanzahl} - 1) × 2 × ${sondenabstand} × 2 + ${zuschlagLinks} + ${zuschlagRechts} = ${totalMm}mm`;
    } else {
        // I-Form: (sondenanzahl - 1) × sondenabstand × 2 + zuschläge
        totalMm = (sondenanzahl - 1) * sondenabstand * 2 + zuschlagLinks + zuschlagRechts;
        formula = `I-Form: (${sondenanzahl} - 1) × ${sondenabstand} × 2 + ${zuschlagLinks} + ${zuschlagRechts} = ${totalMm}mm`;
    }
    
    const totalMeters = (totalMm / 1000).toFixed(2);
    $('#hvbLengthDisplay').text(`${totalMm}mm (${totalMeters}m)`);
    $('#hvbLengthFormula').text(formula);
}

function updateProbeDistanceDisplay() {
    const sondenanzahlInput = $('#sondenanzahl').val();
    const sondenanzahl = sondenanzahlInput ? parseFloat(sondenanzahlInput) : 0;
    const sondenabstandVal = $('#sondenabstandAlt').val() || $('#sondenabstand').val();
    const sondenabstand = sondenabstandVal ? parseFloat(sondenabstandVal) : 0;
    const anschlussart = $('#anschlussartAlt').val() || $('#anschlussart').val();
    
    if (!anschlussart || anschlussart === '') {
        $('#probeDistanceDisplay').text('–');
        $('#probeDistanceFormula').text('Bitte Anschlussart wählen.');
        return;
    }
    
    if (!sondenanzahlInput || sondenanzahlInput === '' || isNaN(sondenanzahl) || sondenanzahl < 1) {
        $('#probeDistanceDisplay').text('–');
        $('#probeDistanceFormula').text('Bitte Anzahl der Sonden eingeben.');
        return;
    }
    
    if (!sondenabstandVal || sondenabstandVal === '' || isNaN(sondenabstand) || sondenabstand <= 0) {
        $('#probeDistanceDisplay').text('–');
        $('#probeDistanceFormula').text('Bitte den Sondenabstand wählen.');
        return;
    }
    
    let totalMm;
    let formula;
    
    if (anschlussart === 'beidseitig') {
        // Beidseitig: (je Seite Math.ceil(probes/2) - 1) × distance
        const probesPerSide = Math.ceil(sondenanzahl / 2);
        const effectiveProbes = Math.max(probesPerSide - 1, 0);
        totalMm = effectiveProbes * sondenabstand;
        formula = `${sondenanzahl} probes, both sides: (je Seite ${probesPerSide} - 1) × ${sondenabstand}mm = ${totalMm}mm`;
    } else {
        // Einseitig: (sondenanzahl - 1) × sondenabstand
        totalMm = (sondenanzahl - 1) * sondenabstand;
        formula = `${sondenanzahl} probes, one side: (${sondenanzahl}-1) × ${sondenabstand}mm = ${totalMm}mm`;
    }
    
    const totalMeters = (totalMm / 1000).toFixed(2);
    $('#probeDistanceDisplay').text(`${totalMm}mm (${totalMeters}m)`);
    $('#probeDistanceFormula').text(formula);
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
        dfm_category: $('#dfmCategory').val(),
        bauform: $('#bauform').val(),
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
        ['Bauform', configurationData.bauform === 'U' ? 'U-Form' : 'I-Form'],
        ['Anzahl Sonden', configurationData.sondenanzahl],
        ['Sondenabstand', `${configurationData.sondenabstand}mm`],
        ['Anschlussart', configurationData.anschlussart],
        ['Kugelhahn-Typ', configurationData.kugelhahn_type || 'Nicht ausgewählt'],
        ['DFM-Kategorie', configurationData.dfm_category || 'Nicht ausgewählt'],
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
                    <p><strong>Mutterartikel:</strong> <code>${data.mother_article_number}</code></p>
                    <p>${data.message}</p>
                    <div class="mb-3">
                        <label class="form-label">Kindartikelnummer:</label>
                        <input type="text" class="form-control" id="childArticleNumber" 
                               value="${data.suggested_child_number}" required>
                        <small class="form-text text-muted">Vollständige Artikelnummer: <code>${data.suggested_child_number}</code></small>
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
    
    // Refresh dynamic fields before sending
    configurationData.dfm_category = $('#dfmCategory').val();
    configurationData.dfm_type = $('#dfmType').val();
    configurationData.kugelhahn_type = $('#kugelhahnType').val();
    configurationData.bauform = $('#bauform').val();
    
    // Update configuration data with article numbers
    if ($('#childArticleNumber').length) {
        const childNumber = $('#childArticleNumber').val();
        configurationData.child_article_number = childNumber;
        // If child number is in format "1000089-002", also set mother_article_number
        if (childNumber && childNumber.includes('-')) {
            const parts = childNumber.split('-');
            if (parts.length >= 2) {
                configurationData.mother_article_number = parts[0];
                configurationData.child_article_number = parts.slice(1).join('-'); // Handle cases like "1000089-002-003"
            }
        } else if (configurationData.mother_article_number) {
            // If we have mother article number from check, use it
            configurationData.child_article_number = childNumber;
        }
    }
    if ($('#newArticleNumber').length) {
        const newNumber = $('#newArticleNumber').val();
        configurationData.full_article_number = newNumber;
        // If new number is in format "1000089-001", extract mother and child
        if (newNumber && newNumber.includes('-')) {
            const parts = newNumber.split('-');
            if (parts.length >= 2) {
                configurationData.mother_article_number = parts[0];
                configurationData.child_article_number = parts.slice(1).join('-');
            }
        }
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
        error: function(xhr, status, error) {
            BOMConfigurator.hideLoading(generateBtn);
            let errorMessage = 'Fehler beim Generieren der BOM.';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                errorMessage = xhr.responseJSON.message;
            } else if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMessage = `Fehler: ${xhr.responseJSON.error}`;
            } else if (xhr.responseText) {
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    errorMessage = errorData.message || errorData.error || errorMessage;
                } catch (e) {
                    errorMessage = `Fehler: ${xhr.status} ${xhr.statusText}`;
                }
            }
            console.error('BOM Generation Error:', xhr.responseJSON || xhr.responseText);
            BOMConfigurator.showAlert(errorMessage, 'danger');
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
        let mengeValue = parseFloat(item.menge);
        console.log(`DEBUG JS: Article ${item.artikelnummer}, Raw menge: ${item.menge}, Type: ${typeof item.menge}, Parsed: ${mengeValue}`);
        
        // Check if value seems suspiciously large (might be 1000x too large)
        // For most BOM items, quantities should be reasonable (less than 1000 for single items)
        if (mengeValue > 100 && mengeValue % 1000 === 0 && mengeValue < 100000) {
            console.warn(`WARNING: Suspiciously large value ${mengeValue} for article ${item.artikelnummer} - might be 1000x too large!`);
            console.warn(`If divided by 1000, would be: ${mengeValue / 1000}`);
        }
        
        const formattedMenge = BOMConfigurator.formatNumber(mengeValue, 3);
        console.log(`DEBUG JS: Formatted: ${formattedMenge}`);
        html += `
            <tr>
                <td>${index + 1}</td>
                <td><code>${item.artikelnummer}</code></td>
                <td>${item.artikelbezeichnung}</td>
                <td>${formattedMenge}</td>
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

// Manual test function to populate alternative dropdown (for debugging)
window.testPopulateAlternativeDropdown = function() {
    console.log('=== Manual test: Populate Alternative Dropdown ===');
    const mainDropdown = $('#sondenabstand');
    const altDropdown = $('#sondenabstandAlt');
    
    console.log('Main dropdown found:', mainDropdown.length > 0);
    console.log('Alt dropdown found:', altDropdown.length > 0);
    
    if (mainDropdown.length && altDropdown.length) {
        const mainOptions = mainDropdown.html();
        const mainOptionCount = mainDropdown.find('option').length;
        
        console.log('Main dropdown has', mainOptionCount, 'options');
        console.log('Main dropdown HTML:', mainOptions);
        
        if (mainOptionCount > 1) {
            altDropdown.html(mainOptions);
            const altOptionCount = altDropdown.find('option').length;
            console.log('Copied to alternative dropdown. Now has', altOptionCount, 'options');
            
            if (altOptionCount > 0) {
                console.log('SUCCESS! Alternative dropdown populated.');
                return true;
            } else {
                console.error('FAILED! Alternative dropdown still empty.');
                return false;
            }
        } else {
            console.error('Main dropdown has no options to copy');
            return false;
        }
    } else {
        console.error('One or both dropdowns not found');
        return false;
    }
};

// Export functions for global use
window.nextStep = nextStep;
window.previousStep = previousStep;
window.generateBOM = generateBOM;
window.printBOM = printBOM;
window.testSondenAPI = testSondenAPI;
window.syncAlternativeSondenabstandDropdown = syncAlternativeSondenabstandDropdown;
