// BOM Configurator JavaScript

let currentStep = 1;
let configurationData = window.initialConfigurationData || {};
let gnxArticles = [];
let hvbStuetzeArticles = [];

function isGNXSchachttyp(schachttyp) {
    return ['GN X1', 'GN X2', 'GN X3', 'GN X4'].includes(schachttyp);
}

$(document).ready(function() {
    // Merge copy-from data into configurationData early so all restore logic can use it
    if (window.initialConfigurationData && Object.keys(window.initialConfigurationData).length > 0) {
        configurationData = { ...configurationData, ...window.initialConfigurationData };
    }

    // Initialize form validation
    initializeValidation();
    
    // Initialize dropdowns
    $('#sondenDurchmesser').html('<option value="">Erst Schachttyp wählen...</option>');
    $('#sondenabstand').html('<option value="">Erst Anschlussart wählen...</option>');
    
    // Event handlers
    $('#anschlussart').on('change', updateSondenabstandOptions);
    // Note: updateSondenanzahlRange is now based on Schachtgrenze (schachttyp), not sondenDurchmesser
    // But we keep the handler for backward compatibility
    $('#sondenDurchmesser').on('change', function() {
        // Range is set by schachttyp, but we can validate the current value
        validateSondenanzahl();
    });

    // Enforce sondenanzahl range not just via arrows but also for keyboard input.
    // We do NOT auto-correct out-of-range values; instead we mark the field invalid
    // and block navigation to the next step until the user fixes it.
    $('#sondenanzahl').on('input change blur', function() {
        validateSondenanzahl();
    });
    // Sonden Durchmesser dropdown is now based only on Schachttyp (from CSV)
    // But only load it when entering step 2, not when Schachttyp changes in step 1
    $('#schachttyp').on('change', function() {
        updateHvbOptions();
        checkGNXChamber();
        updateSondenanzahlFromSchachtgrenze();
        // Update HVB Stütze visibility based on Schachttyp
        loadHVBStuetzeArticles();
        // Don't update Sonden Durchmesser here - it will be loaded when entering step 2
    });
    
    // Initialize sondenanzahl range if schachttyp is already selected (e.g., on page load)
    if ($('#schachttyp').val()) {
        updateSondenanzahlFromSchachtgrenze();
    }
    $('#hvbSize').on('change', function() {
        loadGNXArticles();
        loadHVBStuetzeArticles();
        updateWPOptions();
    });
    $('#wpDiameter').on('change', function() {
        const wpVal = $(this).val();
        const $wpPipe = $('#wpPipeLength');
        const $wpPipeHint = $('#wpPipeLengthHint');
        if ($wpPipe.length === 0) {
            return;
        }
        if (wpVal) {
            // If we already have a saved value in configurationData, prefer it;
            // otherwise default to 1 m whenever a WP diameter is selected.
            const existing = configurationData.wp_pipe_length;
            if (existing !== undefined && existing !== null && existing !== '') {
                $wpPipe.val(existing);
            } else {
                $wpPipe.val('1');
            }
            $wpPipe.prop('disabled', false);
            $wpPipe.removeClass('is-invalid').addClass('is-valid');
            if ($wpPipeHint.length) {
                $wpPipeHint.text('Rohrlänge für den WP-Anschluss in Metern (Standard: 1 m).');
            }
        } else {
            $wpPipe.val('');
            $wpPipe.prop('disabled', true);
            $wpPipe.removeClass('is-valid is-invalid');
            if ($wpPipeHint.length) {
                $wpPipeHint.text('Kein WP-Durchmesser ausgewählt.');
            }
        }
    });

    // On initial load, keep WP-Rohr length disabled until a WP-Durchmesser is selected.
    const initialWpSelectVal = $('#wpDiameter').val();
    const $initialWpPipe = $('#wpPipeLength');
    const $initialWpPipeHint = $('#wpPipeLengthHint');
    if ($initialWpPipe.length) {
        if (initialWpSelectVal) {
            $initialWpPipe.val('1');
            $initialWpPipe.prop('disabled', false);
            $initialWpPipe.addClass('is-valid');
            if ($initialWpPipeHint.length) {
                $initialWpPipeHint.text('Rohrlänge für den WP-Anschluss in Metern (Standard: 1 m).');
            }
        } else {
            $initialWpPipe.val('');
            $initialWpPipe.prop('disabled', true);
            $initialWpPipe.removeClass('is-valid is-invalid');
            if ($initialWpPipeHint.length) {
                $initialWpPipeHint.text('Kein WP-Durchmesser ausgewählt.');
            }
        }
    }
    $('#dfmCategory').on('change', handleDFMCategoryChange);
    $('#dfmType').on('change', function() {
        // When dfmType changes, just ensure D-Kugelhahn section is hidden if needed
        if ($('#dfmType').val() !== 'Kugelhahn-Typ') {
            $('#dfmKugelhahnTypeSection').hide();
        }
    });
    
    // Update compatible Kugelhahn options whenever HVB or probe diameter changes
    $('#hvbSize').on('change', updateKugelhahnOptions);
    $('#sondenDurchmesser').on('change', updateKugelhahnOptions);
    
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
    
    // Update HVB options if Schachttyp is already selected
    if ($('#schachttyp').val()) {
        updateHvbOptions();
    }
    
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

    // ---- COPY-FROM: prefill all fields and trigger dependent AJAX chains ----
    if (window.initialConfigurationData && Object.keys(window.initialConfigurationData).length > 0) {
        const cd = window.initialConfigurationData;

        // Step 1 direct fields
        $('#configName').val(cd.configuration_name || '');
        $('#bauform').val(cd.bauform || 'I');
        $('#zuschlagLinks').val(cd.zuschlag_links || '100');
        $('#zuschlagRechts').val(cd.zuschlag_rechts || '100');
        $('#sondenanzahl').val(cd.sondenanzahl || '');

        // Step 2: optional lengths (mark as manual so DB defaults don't override)
        if (cd.vorlauf_length_per_probe) {
            $('#vorlauflengthperprobe').val(cd.vorlauf_length_per_probe);
            _probeLengthManualVorlauf = true;
        }
        if (cd.ruecklauf_length_per_probe) {
            $('#ruecklauflengthperprobe').val(cd.ruecklauf_length_per_probe);
            _probeLengthManualRuecklauf = true;
        }

        // Set schachttyp (triggers HVB filter, GNX check, etc. via change handler)
        if (cd.schachttyp) {
            $('#schachttyp').val(cd.schachttyp).trigger('change');
        }

        // After HVB options are loaded, set hvbSize and its dependants
        setTimeout(function() {
            if (cd.hvb_size) {
                const $hvb = $('#hvbSize');
                if ($hvb.find(`option[value="${cd.hvb_size}"]`).length > 0) {
                    $hvb.val(cd.hvb_size);
                }
                $hvb.trigger('change');
            }

            // After WP options load, restore WP diameter
            setTimeout(function() {
                if (cd.wp_diameter) {
                    const $wp = $('#wpDiameter');
                    if ($wp.find(`option[value="${cd.wp_diameter}"]`).length > 0) {
                        $wp.val(cd.wp_diameter).trigger('change');
                    }
                }
                // Restore WP pipe length after WP diameter change has settled
                setTimeout(function() {
                    if (cd.wp_pipe_length) {
                        $('#wpPipeLength').val(cd.wp_pipe_length);
                    }
                }, 400);
            }, 600);

            // Restore HVB Stütze custom quantities after they load
            setTimeout(function() {
                if (cd.hvb_stuetze_quantities && typeof cd.hvb_stuetze_quantities === 'object') {
                    Object.entries(cd.hvb_stuetze_quantities).forEach(function([artNr, qty]) {
                        const $input = $(`#hvb-stuetze-qty-${artNr}`);
                        if ($input.length) {
                            $input.val(qty);
                            configurationData[`hvb_stuetze_${artNr}`] = String(qty);
                        }
                    });
                }
            }, 1200);
        }, 600);

        // Step 2: anschlussart triggers sondenabstand loading
        if (cd.anschlussart) {
            $('#anschlussart').val(cd.anschlussart).trigger('change');
        }

        // After sondenabstand AJAX finishes and rebuilds the dropdown (with Standard pre-selected),
        // force the copied value on top. We use a longer delay to ensure the AJAX callback is done.
        function forceRestoreSondenabstand() {
            if (cd.sondenabstand) {
                const saved = String(cd.sondenabstand);
                const $sa = $('#sondenabstand');
                const $saAlt = $('#sondenabstandAlt');
                if ($sa.find(`option[value="${saved}"]`).length > 0) {
                    $sa.val(saved);
                    $sa.removeClass('is-invalid').addClass('is-valid');
                }
                if ($saAlt.length && $saAlt.find(`option[value="${saved}"]`).length > 0) {
                    $saAlt.val(saved);
                }
            }
        }
        setTimeout(forceRestoreSondenabstand, 1200);
        setTimeout(forceRestoreSondenabstand, 2000);

        // Step 3: DFM category + type
        if (cd.dfm_category) {
            $('#dfmCategory').val(cd.dfm_category);
            if (cd.dfm_type) {
                $('#dfmType').data('previous-value', cd.dfm_type);
            }
            handleDFMCategoryChange();
        }

        // Apply is-valid ticks to every prefilled field after all AJAX has settled
        setTimeout(function() {
            applyCopyTicks();
        }, 2500);
    }
});

function applyCopyTicks() {
    $('#bomConfigForm .form-control, #bomConfigForm .form-select').each(function() {
        const $el = $(this);
        const val = $el.val();
        if (val && val !== '') {
            $el.removeClass('is-invalid').addClass('is-valid');
        }
    });
}

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

    // Additional semantic validation for specific steps.
    // For step 2, ensure sondenanzahl is within the allowed min/max range
    // and that WP-Rohr-Länge is set when a WP-Durchmesser is selected.
    if (step === 2) {
        if (!validateSondenanzahl()) {
            isValid = false;
        }

        const wpVal = $('#wpDiameter').val();
        const $wpPipe = $('#wpPipeLength');
        if (wpVal && $wpPipe.length) {
            const pipeValRaw = $wpPipe.val();
            if (!pipeValRaw && pipeValRaw !== 0) {
                // Mark as invalid and block navigation if empty while WP is selected
                $wpPipe.removeClass('is-valid').addClass('is-invalid');
                isValid = false;
            }
        }
    }
    
    return isValid;
}

// Field label mapping for summary display
const fieldLabels = {
    'configuration_name': 'Konfigurationsname',
    'schachttyp': 'Schachttyp',
    'hvb_size': 'HVB-Größe',
    'wp_diameter': 'WP-Durchmesser',
    'wp_diameter': 'WP-Durchmesser',
    'anschlussart': 'Anschlussart',
    'sonden_durchmesser': 'Sonden-Durchmesser',
    'sondenanzahl': 'Anzahl Sonden',
    'sondenabstand': 'Sondenabstand',
    'bauform': 'Bauform',
    'zuschlag_links': 'Zuschlag Links',
    'zuschlag_rechts': 'Zuschlag Rechts',
    'wp_pipe_length': 'WP-Rohr-Länge',
    'vorlauf_length_per_probe': 'Vorlauf-Länge pro Sonde',
    'ruecklauf_length_per_probe': 'Rücklauf-Länge pro Sonde',
    'kugelhahn_type': 'Kugelhahn-Typ',
    'dfm_category': 'DFM-Kategorie',
    'dfm_type': 'DFM-Typ',
    'dfm_kugelhahn_type': 'D-Kugelhahn-Typ'
};

// Step field mapping - which fields belong to which step
const stepFields = {
    1: ['configuration_name', 'schachttyp', 'hvb_size', 'wp_diameter'],
    2: ['anschlussart', 'sonden_durchmesser', 'sondenanzahl', 'sondenabstand', 'bauform', 'zuschlag_links', 'zuschlag_rechts', 'wp_pipe_length', 'vorlauf_length_per_probe', 'ruecklauf_length_per_probe'],
    3: ['kugelhahn_type', 'dfm_category', 'dfm_type', 'dfm_kugelhahn_type']
};

function formatFieldValue(fieldName, value) {
    if (!value || value === '') return 'Nicht ausgewählt';
    
    // Format specific fields
    if (fieldName === 'hvb_size') return `${value} mm`;
    if (fieldName === 'wp_diameter') return `DA ${value} mm`;
    if (fieldName === 'sonden_durchmesser') return `${value} mm`;
    if (fieldName === 'sondenabstand') return `${value} mm`;
    if (fieldName === 'bauform') return value === 'U' ? 'U-Form' : 'I-Form';
    if (fieldName === 'anschlussart') return value === 'einseitig' ? 'Einseitig' : 'Beidseitig';
    if (fieldName === 'dfm_category') return value === 'plastic' ? 'Kunststoff' : value === 'brass' ? 'Messing' : value;
    if (fieldName === 'vorlauf_length_per_probe') return `${value} m`;
    if (fieldName === 'ruecklauf_length_per_probe') return `${value} m`;
    
    return value;
}

// Field ID mapping - maps field names to actual DOM IDs
const fieldIdMap = {
    'configuration_name': 'configName',
    'schachttyp': 'schachttyp',
    'hvb_size': 'hvbSize',
    'wp_diameter': 'wpDiameter',
    'wp_diameter': 'wpDiameter',
    'wp_pipe_length': 'wpPipeLength',
    'anschlussart': 'anschlussart',
    'sonden_durchmesser': 'sondenDurchmesser',
    'sondenanzahl': 'sondenanzahl',
    'sondenabstand': 'sondenabstand',
    'bauform': 'bauform',
    'zuschlag_links': 'zuschlagLinks',
    'zuschlag_rechts': 'zuschlagRechts',
    'vorlauf_length_per_probe': 'vorlauflengthperprobe',
    'ruecklauf_length_per_probe': 'ruecklauflengthperprobe',
    'kugelhahn_type': 'kugelhahnType',
    'dfm_category': 'dfmCategory',
    'dfm_type': 'dfmType',
    'dfm_kugelhahn_type': 'dfmKugelhahnType'
};

function getStepSummary(stepNumber) {
    const summary = [];
    
    if (stepFields[stepNumber]) {
        stepFields[stepNumber].forEach(fieldName => {
            const fieldId = fieldIdMap[fieldName] || fieldName.replace(/_/g, '');
            let value = '';
            
            // Prioritize configurationData since form fields might not be accessible in step 5
            if (configurationData[fieldName]) {
                value = configurationData[fieldName];
            } else {
                // Fallback to form field if available
                const $field = $(`#${fieldId}`);
                if ($field.length) {
                    value = $field.val() || '';
                }
            }
            
            if (value) {
                const label = fieldLabels[fieldName] || fieldName;
                const formattedValue = formatFieldValue(fieldName, value);
                summary.push([label, formattedValue]);
            }
        });
    }
    
    return summary;
}

function updateStepSummary(step) {
    // Only show summary for steps 2, 3, and 4
    if (step < 2 || step > 4) return;
    
    if (step === 2) {
        // Step 2: Show only Step 1 summary
        const step1Summary = getStepSummary(1);
        const $summaryContainer = $(`#config-step-${step} .step-1-summary`);
        
        if ($summaryContainer.length && step1Summary.length > 0) {
            let html = '<div class="table-responsive"><table class="table table-sm table-borderless" style="width: auto;"><tbody>';
            step1Summary.forEach(function(row) {
                html += `<tr><td><strong>${row[0]}:</strong></td><td>${row[1]}</td></tr>`;
            });
            html += '</tbody></table></div>';
            $summaryContainer.html(html);
            $summaryContainer.closest('.summary-section').removeClass('d-none');
        } else if ($summaryContainer.length && step1Summary.length === 0) {
            $summaryContainer.closest('.summary-section').addClass('d-none');
        }
    } else if (step === 3) {
        // Step 3: Show Step 1 in left box, Step 2 in right box
        const step1Summary = getStepSummary(1);
        const step2Summary = getStepSummary(2);
        
        // Update Step 1 summary (left box)
        const $step1Container = $(`#config-step-${step} .step-1-summary`);
        if ($step1Container.length && step1Summary.length > 0) {
            let html = '<div class="table-responsive"><table class="table table-sm table-borderless" style="width: auto;"><tbody>';
            step1Summary.forEach(function(row) {
                html += `<tr><td><strong>${row[0]}:</strong></td><td>${row[1]}</td></tr>`;
            });
            html += '</tbody></table></div>';
            $step1Container.html(html);
            $step1Container.closest('.summary-section').removeClass('d-none');
        } else if ($step1Container.length && step1Summary.length === 0) {
            $step1Container.closest('.summary-section').addClass('d-none');
        }
        
        // Update Step 2 summary (right box)
        const $step2Container = $(`#config-step-${step} .step-2-summary`);
        if ($step2Container.length && step2Summary.length > 0) {
            let html = '<div class="table-responsive"><table class="table table-sm table-borderless" style="width: auto;"><tbody>';
            step2Summary.forEach(function(row) {
                html += `<tr><td><strong>${row[0]}:</strong></td><td>${row[1]}</td></tr>`;
            });
            html += '</tbody></table></div>';
            $step2Container.html(html);
            $step2Container.closest('.summary-section').removeClass('d-none');
        } else if ($step2Container.length && step2Summary.length === 0) {
            $step2Container.closest('.summary-section').addClass('d-none');
        }
    } else if (step === 4) {
        // Step 4: Show Step 1, Step 2, and Step 3 summaries in three columns
        const step1Summary = getStepSummary(1);
        const step2Summary = getStepSummary(2);
        const step3Summary = getStepSummary(3);
        
        // Update Step 1 summary (first column)
        const $step1Container = $(`#config-step-${step} .step-1-summary`);
        if ($step1Container.length && step1Summary.length > 0) {
            let html = '<div class="table-responsive"><table class="table table-sm table-borderless" style="width: auto;"><tbody>';
            step1Summary.forEach(function(row) {
                html += `<tr><td><strong>${row[0]}:</strong></td><td>${row[1]}</td></tr>`;
            });
            html += '</tbody></table></div>';
            $step1Container.html(html);
            $step1Container.closest('.summary-section').removeClass('d-none');
        } else if ($step1Container.length && step1Summary.length === 0) {
            $step1Container.closest('.summary-section').addClass('d-none');
        }
        
        // Update Step 2 summary (second column)
        const $step2Container = $(`#config-step-${step} .step-2-summary`);
        if ($step2Container.length && step2Summary.length > 0) {
            let html = '<div class="table-responsive"><table class="table table-sm table-borderless" style="width: auto;"><tbody>';
            step2Summary.forEach(function(row) {
                html += `<tr><td><strong>${row[0]}:</strong></td><td>${row[1]}</td></tr>`;
            });
            html += '</tbody></table></div>';
            $step2Container.html(html);
            $step2Container.closest('.summary-section').removeClass('d-none');
        } else if ($step2Container.length && step2Summary.length === 0) {
            $step2Container.closest('.summary-section').addClass('d-none');
        }
        
        // Update Step 3 summary (third column)
        const $step3Container = $(`#config-step-${step} .step-3-summary`);
        if ($step3Container.length && step3Summary.length > 0) {
            let html = '<div class="table-responsive"><table class="table table-sm table-borderless" style="width: auto;"><tbody>';
            step3Summary.forEach(function(row) {
                html += `<tr><td><strong>${row[0]}:</strong></td><td>${row[1]}</td></tr>`;
            });
            html += '</tbody></table></div>';
            $step3Container.html(html);
            $step3Container.closest('.summary-section').removeClass('d-none');
        } else if ($step3Container.length && step3Summary.length === 0) {
            $step3Container.closest('.summary-section').addClass('d-none');
        }
    }
}

function nextStep(step) {
    if (!validateStep(currentStep)) {
        BOMConfigurator.showAlert('Bitte füllen Sie alle Pflichtfelder aus.', 'warning');
        return;
    }
    
    // Save current step data before moving
    saveStepData(currentStep);
    
    // Hide current step
    $(`#config-step-${currentStep}`).addClass('d-none');
    
    // Update step indicators
    $(`#step-${currentStep}`).removeClass('active').addClass('completed');
    $(`#step-${step}`).addClass('active');
    
    // Show next step FIRST so elements are in DOM
    $(`#config-step-${step}`).removeClass('d-none').addClass('fade-in');
    
    currentStep = step;
    
    // Update summary for current step
    updateStepSummary(step);
    
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
            loadHVBStuetzeArticles();
            // Auto-fill probe lengths from DB
            loadProbeLengths();
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

            // Initialize WP-Rohr-Länge default when entering step 2
            const wpVal = $('#wpDiameter').val();
            const $wpPipe = $('#wpPipeLength');
            const $wpPipeHint = $('#wpPipeLengthHint');
            if ($wpPipe.length) {
                if (wpVal) {
                    const existing = configurationData.wp_pipe_length;
                    if (existing !== undefined && existing !== null && existing !== '') {
                        $wpPipe.val(existing);
                    } else {
                        $wpPipe.val('1');
                    }
                    $wpPipe.prop('disabled', false);
                    $wpPipe.removeClass('is-invalid').addClass('is-valid');
                    if ($wpPipeHint.length) {
                        $wpPipeHint.text('Rohrlänge für den WP-Anschluss in Metern (Standard: 1 m).');
                    }
                } else {
                    $wpPipe.val('');
                    $wpPipe.prop('disabled', true);
                    $wpPipe.removeClass('is-valid is-invalid');
                    if ($wpPipeHint.length) {
                        $wpPipeHint.text('Kein WP-Durchmesser ausgewählt.');
                    }
                }
            }
        }, 300);
    }
    
    // Special handling for step 3 - ensure DFM dropdown visibility is correct
    if (step === 3) {
        setTimeout(function() {
            // Check if dfmCategory is set to "kugelhahn" and show dropdown if needed
            const category = $('#dfmCategory').val();
            if (category === 'kugelhahn') {
                $('#dfmKugelhahnTypeSection').show();
            }
            // Refresh Kugelhahn compatibility options when entering step 3
            updateKugelhahnOptions();
        }, 100);
    }
    
    // Special handling for step 4 (configuration check)
    if (step === 4) {
        // Save all data before checking
        saveStepData(1);
        saveStepData(2);
        saveStepData(3);
        // Update summaries after data is saved
        setTimeout(function() {
            updateStepSummary(4);
            checkConfiguration();
        }, 100);
    }
    
    // Scroll to top
    $('html, body').animate({ scrollTop: 0 }, 500);
}

function saveStepData(step) {
    // Save data from current step to configurationData
    if (stepFields[step]) {
        stepFields[step].forEach(fieldName => {
            // Map from field name to DOM ID
            const fieldId = fieldIdMap[fieldName] || fieldName.replace(/_/g, '');
            const $field = $(`#${fieldId}`);
            if ($field.length) {
                configurationData[fieldName] = $field.val() || '';
            }
        });
    }
    
    // Also save HVB Stuetze quantities if we're in step 2
    if (step === 2 && hvbStuetzeArticles.length > 0) {
        hvbStuetzeArticles.forEach(function(article) {
            const quantityInput = $(`#hvb-stuetze-qty-${article.artikelnummer}`);
            if (quantityInput.length) {
                configurationData[`hvb_stuetze_${article.artikelnummer}`] = quantityInput.val() || '1';
            }
        });
    }
}

function previousStep(step) {
    // Save current step data before moving
    saveStepData(currentStep);
    
    // Hide current step
    $(`#config-step-${currentStep}`).addClass('d-none');
    
    // Update step indicators
    $(`#step-${currentStep}`).removeClass('active');
    $(`#step-${step}`).removeClass('completed').addClass('active');
    
    // Show previous step FIRST so elements are in DOM
    $(`#config-step-${step}`).removeClass('d-none').addClass('fade-in');
    
    currentStep = step;
    
    // Update summary for current step
    updateStepSummary(step);
    
    // Ensure sonden options are loaded when going back to step 2
    if (step === 2) {
        // Wait a bit for DOM to be ready
        setTimeout(function() {
            console.log('Returning to Step 2 - checking dropdowns...');
            console.log('sondenabstandAlt exists:', $('#sondenabstandAlt').length > 0);
            
            updateSondenOptions();
            // Load HVB Stuetze articles if HVB size is selected
            loadHVBStuetzeArticles();
            // Auto-fill probe lengths from DB
            loadProbeLengths();
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

// Store original HVB options for restoration
let originalHvbOptions = null;

function updateHvbOptions() {
    const schachttyp = $('#schachttyp').val();
    const $hvbSelect = $('#hvbSize');
    
    // Store original options if not already stored
    if (!originalHvbOptions) {
        originalHvbOptions = $hvbSelect.html();
    }
    
    if (!schachttyp) {
        // If no Schachttyp selected, restore all options
        $hvbSelect.html(originalHvbOptions);
        return;
    }
    
    const currentValue = $hvbSelect.val();
    
    $.ajax({
        url: '/api/allowed-hvb-sizes/',
        method: 'POST',
        data: JSON.stringify({
            schachttyp: schachttyp
        }),
        contentType: 'application/json',
        success: function(data) {
            console.log('Allowed HVB sizes response:', data);
            
            if (data.error) {
                console.error('Error getting allowed HVB sizes:', data.error);
                // On error, restore all options
                $hvbSelect.html(originalHvbOptions);
                return;
            }
            
            const allowedSizes = data.allowed_sizes || [];
            const allAllowed = data.all_allowed || false;
            
            console.log('Allowed sizes:', allowedSizes, 'All allowed:', allAllowed);
            
            if (allAllowed || allowedSizes.length === 0) {
                // No restrictions, restore all options
                console.log('No restrictions - showing all HVB options');
                $hvbSelect.html(originalHvbOptions);
                // Restore saved HVB value after repopulating
                const savedHvb = configurationData.hvb_size;
                if (savedHvb && $hvbSelect.find(`option[value="${savedHvb}"]`).length > 0) {
                    $hvbSelect.val(savedHvb);
                }
            } else {
                console.log('Filtering HVB options to:', allowedSizes);
                
                // Rebuild options with only allowed sizes
                let newOptions = '<option value="">Bitte wählen...</option>';
                
                // Parse original options and filter
                const $originalOptions = $(originalHvbOptions);
                $originalOptions.each(function() {
                    const $option = $(this);
                    const optionValue = $option.val();
                    
                    if (!optionValue) {
                        // Keep the "Bitte wählen..." option
                        return;
                    }
                    
                    // Extract size number from option value
                    let sizeNumber = optionValue.toString().trim();
                    if (sizeNumber.toLowerCase().endsWith('mm')) {
                        sizeNumber = sizeNumber.slice(0, -2).trim();
                    }
                    
                    // Also check the option text
                    const optionText = $option.text().trim();
                    let textSizeNumber = optionText;
                    if (textSizeNumber.toLowerCase().endsWith('mm')) {
                        textSizeNumber = textSizeNumber.slice(0, -2).trim();
                    }
                    
                    // Use the size number from value or text
                    const finalSize = sizeNumber || textSizeNumber;
                    
                    // Check if this size is in allowed list
                    if (allowedSizes.includes(finalSize)) {
                        newOptions += `<option value="${optionValue}">${optionText}</option>`;
                    }
                });
                
                $hvbSelect.html(newOptions);
                
                // Restore saved HVB value or current selection
                const savedHvb = configurationData.hvb_size;
                if (savedHvb && $hvbSelect.find(`option[value="${savedHvb}"]`).length > 0) {
                    $hvbSelect.val(savedHvb);
                } else if (currentValue) {
                    const currentSize = currentValue.toString().trim().replace(/mm$/i, '');
                    if (allowedSizes.includes(currentSize)) {
                        $hvbSelect.val(currentValue);
                    }
                }
            }
        },
        error: function(xhr, status, error) {
            console.error('Error fetching allowed HVB sizes:', error);
            // On error, restore all options
            $hvbSelect.html(originalHvbOptions);
        }
    });
}

function updateSondenOptions() {
    // Check if dropdown exists (only exists in step 2)
    if ($('#sondenDurchmesser').length === 0) {
        console.log('Sonden Durchmesser dropdown not found - probably still in step 1');
        return;
    }
    
    // Get values directly from DOM elements (most reliable)
    const schachttyp = $('#schachttyp').val() || '';
    
    console.log('updateSondenOptions called - schachttyp:', schachttyp);
    
    if (!schachttyp) {
        $('#sondenDurchmesser').html('<option value="">Erst Schachttyp wählen...</option>');
        return;
    }
    
    // Clean values
    const cleanSchachttyp = schachttyp.trim();
    
    // Show loading state
    $('#sondenDurchmesser').html('<option value="">Lade Optionen...</option>');
    
    // Make AJAX request to get Sonden Durchmesser options from CSV
    $.ajax({
        url: '/api/sonden-durchmesser-options/',
        method: 'POST',
        cache: false,
        data: JSON.stringify({
            schachttyp: cleanSchachttyp
        }),
        contentType: 'application/json',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        success: function(data) {
            console.log('API success - Sonden Durchmesser options count:', data.sonden_durchmesser_options ? data.sonden_durchmesser_options.length : 0);
            
            let options = '<option value="">Bitte wählen...</option>';
            
            if (data.sonden_durchmesser_options && data.sonden_durchmesser_options.length > 0) {
                data.sonden_durchmesser_options.forEach(function(option) {
                    options += `<option value="${option.durchmesser}">${option.label}</option>`;
                });
            } else {
                options = '<option value="">Keine Optionen verfügbar</option>';
                if (data.error) {
                    console.error('API Error:', data.error);
                }
            }
            
            // Only update dropdown if it exists (we're in step 2)
            const $dropdown = $('#sondenDurchmesser');
            if ($dropdown.length > 0) {
                $dropdown.html(options);

            // Restore previously selected value from configurationData (if any)
            const savedValue = configurationData.sonden_durchmesser;
            if (savedValue && $dropdown.find(`option[value="${savedValue}"]`).length > 0) {
                $dropdown.val(savedValue);
                $dropdown.removeClass('is-invalid').addClass('is-valid');
            }
            } else {
                console.log('Sonden Durchmesser dropdown not found - skipping update');
            }
        },
        error: function(xhr, status, error) {
            console.error('AJAX error:', error);
            console.error('Response:', xhr.responseText);
            console.error('Status:', xhr.status);
            // Only update dropdown if it exists (we're in step 2)
            if ($('#sondenDurchmesser').length > 0) {
                $('#sondenDurchmesser').html('<option value="">Fehler beim Laden</option>');
                // Show detailed error in console, but user-friendly message
                const errorMsg = xhr.responseText ? JSON.parse(xhr.responseText).error || 'Unbekannter Fehler' : 'Server-Fehler';
                console.error('Detailed error:', errorMsg);
                if (typeof BOMConfigurator !== 'undefined' && BOMConfigurator.showAlert) {
                    BOMConfigurator.showAlert('Fehler beim Laden der Sonden-Durchmesser-Optionen: ' + errorMsg, 'danger');
                }
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
                           ${option.sondenabstand} mm${hinweis}
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
                
                // Restore a previously saved sondenabstand (from copy or back-navigation) if available.
                // Prefer the value from an initial copied configuration, falling back to configurationData.
                const savedAbstand = initialCopiedSondenabstand || configurationData.sondenabstand;
                if (savedAbstand && $('#sondenabstand').find(`option[value="${savedAbstand}"]`).length > 0) {
                    $('#sondenabstand').val(savedAbstand);
                    if (altDropdown.length > 0) altDropdown.val(savedAbstand);
                    if (altDropdownDom) altDropdownDom.value = savedAbstand;
                    // Don't overwrite zuschlag values when restoring from copy
                    $('#sondenabstand').trigger('change');
                    // Lock to prevent later auto-reset to standard
                    sondenabstandLocked = true;
                    // Only use initialCopiedSondenabstand once
                    initialCopiedSondenabstand = null;
                } else if (standardOption && !sondenabstandLocked) {
                    $('#zuschlagLinks').val(standardOption.zuschlag_links);
                    $('#zuschlagRechts').val(standardOption.zuschlag_rechts);
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

function handleDFMCategoryChange() {
    const category = $('#dfmCategory').val();
    
    // Hide D-Kugelhahn section initially
    $('#dfmKugelhahnTypeSection').hide();
    $('#dfmKugelhahnType').val('');
    
    // If "Kugelhahn-Typ" is selected from category dropdown, show the D-Kugelhahn dropdown
    if (category === 'kugelhahn') {
        $('#dfmKugelhahnTypeSection').show();
        $('#dfmType').html('<option value="">Nicht verfügbar</option>').prop('disabled', true).val('');
        return;
    }
    
    // For other categories, load DFM options normally
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
            
            // Restore previous selection if it exists
            const previousValue = $('#dfmType').data('previous-value');
            if (previousValue && $('#dfmType option[value="' + previousValue + '"]').length > 0) {
                $('#dfmType').val(previousValue);
            }
        },
        error: function() {
            $('#dfmType').html('<option value="">Fehler beim Laden</option>');
            if (typeof BOMConfigurator !== 'undefined' && BOMConfigurator.showAlert) {
                BOMConfigurator.showAlert('Fehler beim Laden der DFM-Optionen.', 'danger');
            }
        }
    });
}

function updateKugelhahnOptions() {
    const hvbSize = $('#hvbSize').val();
    const probeSize = $('#sondenDurchmesser').val();
    const $khSelect = $('#kugelhahnType');
    const $dKhSelect = $('#dfmKugelhahnType');

    if (!$khSelect.length && !$dKhSelect.length) {
        return;
    }

    if (!hvbSize || !probeSize) {
        $khSelect.html('<option value="">Keinen auswählen</option>');
        $dKhSelect.html('<option value="">Bitte wählen...</option>');
        return;
    }

    const csrftoken = $('[name=csrfmiddlewaretoken]').val();

    $.ajax({
        url: '/api/kugelhahn-options/',
        method: 'POST',
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        data: JSON.stringify({
            hvb_size: hvbSize,
            sonden_durchmesser: probeSize
        }),
        success: function(response) {
            const options = response.kugelhahn_options || [];

            // Vorlauf Kugelhahn-Typ
            let khHtml = '<option value="">Keinen auswählen</option>';
            options.forEach(function(type) {
                khHtml += `<option value="${type}">${type}</option>`;
            });
            $khSelect.html(khHtml);

            // Restore previously selected Kugelhahn-Typ if still available
            const savedKhType = configurationData.kugelhahn_type;
            if (savedKhType && $khSelect.find(`option[value="${savedKhType}"]`).length > 0) {
                $khSelect.val(savedKhType);
                $khSelect.removeClass('is-invalid').addClass('is-valid');
            }

            // Rücklauf D-Kugelhahn-Typ
            let dKhHtml = '<option value="">Bitte wählen...</option>';
            options.forEach(function(type) {
                dKhHtml += `<option value="${type}">${type}</option>`;
            });
            $dKhSelect.html(dKhHtml);

            // Restore previously selected D-Kugelhahn-Typ if still available
            const savedDKhType = configurationData.dfm_kugelhahn_type;
            if (savedDKhType && $dKhSelect.find(`option[value="${savedDKhType}"]`).length > 0) {
                $dKhSelect.val(savedDKhType);
                $dKhSelect.removeClass('is-invalid').addClass('is-valid');
            }
        },
        error: function(xhr, status, error) {
            console.error('Error loading Kugelhahn options:', error, xhr.responseText);
            $khSelect.html('<option value="">Keinen auswählen</option>');
            $dKhSelect.html('<option value="">Bitte wählen...</option>');
        }
    });
}

function updateDFMOptions() {
    // This function is kept for backward compatibility but now redirects to handleDFMCategoryChange
    handleDFMCategoryChange();
}

function updateSondenanzahlFromSchachtgrenze() {
    const schachttyp = $('#schachttyp').val();
    
    if (!schachttyp) {
        $('#sondenanzahl').attr('min', 2).removeAttr('max');
        $('#sondenanzahlRange').text('');
        return;
    }
    
    // Get CSRF token
    const csrftoken = $('[name=csrfmiddlewaretoken]').val();
    
    // Fetch max sondenanzahl from Schachtgrenze
    $.ajax({
        url: '/api/schachtgrenze-info/',
        method: 'POST',
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        data: JSON.stringify({ schachttyp: schachttyp }),
        success: function(response) {
            console.log('Schachtgrenze response:', response);
            
            if (response.error) {
                console.warn('Schachtgrenze API returned error:', response.error);
                // Still set min to 2 even if there's an error
                $('#sondenanzahl').attr('min', 2).removeAttr('max');
                $('#sondenanzahlRange').text(`Erlaubter Bereich: 2 - ∞ Sonden (${response.error})`);
                return;
            }
            
            const min = 2; // Always 2 as per requirement
            const max = response.max_sondenanzahl;
            
            $('#sondenanzahl').attr('min', min);
            
            if (max && max > 0) {
                $('#sondenanzahl').attr('max', max);
                $('#sondenanzahlRange').text(`Erlaubter Bereich: ${min} - ${max} Sonden`);
            } else {
                $('#sondenanzahl').removeAttr('max');
                $('#sondenanzahlRange').text(`Erlaubter Bereich: ${min} - ∞ Sonden`);
            }
            
            // After updating the allowed range, validate (but do not auto-correct) the current value.
            validateSondenanzahl();
        },
        error: function(xhr, status, error) {
            console.error('Error fetching Schachtgrenze info:', error, xhr.responseText);
            // Fallback: set min to 2, no max
            $('#sondenanzahl').attr('min', 2).removeAttr('max');
            $('#sondenanzahlRange').text('Fehler beim Laden der Grenzwerte');
            $('#sondenanzahl').addClass('is-invalid');
        }
    });
}

function updateWPOptions() {
    const hvbSize = $('#hvbSize').val();
    const $wpSelect = $('#wpDiameter');
    const $hint = $('#wpDiameterHint');

    // Reset when no HVB is selected
    if (!hvbSize) {
        $wpSelect.html('<option value="">Keinen auswählen</option>').prop('disabled', true);
        $hint.text('');
        return;
    }

    $wpSelect.prop('disabled', false);
    $wpSelect.html('<option value="">Lade WP-Optionen...</option>');
    $hint.text('');

    const csrftoken = $('[name=csrfmiddlewaretoken]').val();

    $.ajax({
        url: '/api/wp-options/',
        method: 'POST',
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        data: JSON.stringify({ hvb_size: hvbSize }),
        success: function(response) {
            const options = response.wp_options || [];
            let html = '<option value="">Keinen auswählen</option>';
            options.forEach(function(dia) {
                html += `<option value="${dia}">DA ${dia} mm</option>`;
            });
            $wpSelect.html(html);

            // Restore saved WP diameter if available
            const savedWp = configurationData.wp_diameter;
            if (savedWp && $wpSelect.find(`option[value="${savedWp}"]`).length > 0) {
                $wpSelect.val(savedWp).trigger('change');
            }

            if (options.length === 0) {
                $hint.text('Für diese HVB-Größe sind keine WP-Durchmesser definiert.');
            } else {
                $hint.text('Wählen Sie den WP-Durchmesser (Wärmepumpenanschluss).');
            }
        },
        error: function(xhr, status, error) {
            console.error('Error loading WP options:', error, xhr.responseText);
            $wpSelect.html('<option value="">Keinen auswählen</option>').prop('disabled', true);
            $hint.text('Fehler beim Laden der WP-Optionen.');
        }
    });
}

function validateSondenanzahl() {
    // Validate current sondenanzahl value against min/max WITHOUT auto-correcting.
    // If out of range, mark the field as invalid and let step validation block navigation.
    const $field = $('#sondenanzahl');
    const rawValue = $field.val();
    const value = parseInt(rawValue, 10);
    const min = parseInt($field.attr('min'), 10) || 2;
    const maxAttr = $field.attr('max');
    const max = maxAttr ? parseInt(maxAttr, 10) : null;

    let isValid = true;

    if (!rawValue || isNaN(value)) {
        isValid = false;
    } else if (value < min) {
        isValid = false;
    } else if (max && value > max) {
        isValid = false;
    }

    $field.removeClass('is-valid is-invalid');
    if (isValid) {
        $field.addClass('is-valid');
    } else {
        $field.addClass('is-invalid');
    }

    return isValid;
}

function updateSondenanzahlRange() {
    // This function is kept for backward compatibility but now uses Schachtgrenze
    // The range is set when schachttyp changes, not when sondenDurchmesser changes
    updateSondenanzahlFromSchachtgrenze();
}

function checkGNXChamber() {
    const schachttyp = $('#schachttyp').val();
    
    if (['GN X1', 'GN X2', 'GN X3', 'GN X4'].includes(schachttyp)) {
        // Don't show section yet - wait for articles to load
        $('#gnxChamberSection').addClass('d-none');
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
            gnxArticles = data.articles || [];
            renderGNXArticles();
        },
        error: function() {
            BOMConfigurator.showAlert('Fehler beim Laden der GN X Artikel.', 'danger');
        }
    });
}

function renderGNXArticles() {
    // Hide section if no articles
    if (!gnxArticles || gnxArticles.length === 0) {
        $('#gnxChamberSection').addClass('d-none');
        return;
    }
    
    // Show section only if there are articles
    $('#gnxChamberSection').removeClass('d-none');
    
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

function loadHVBStuetzeArticles() {
    const schachttyp = $('#schachttyp').val();
    const hvbSize = $('#hvbSize').val();
    
    // Only relevant for GN X chambers
    if (!isGNXSchachttyp(schachttyp)) {
        hvbStuetzeArticles = [];
        $('#hvbStuetzeArticlesList').html('');
        $('#hvbStuetzeSection').addClass('d-none');
        return;
    }
    
    // Show section for GN X chambers
    $('#hvbStuetzeSection').removeClass('d-none');
    
    if (!hvbSize) {
        // Clear the list if no HVB size is selected
        $('#hvbStuetzeArticlesList').html('<p class="text-muted text-center mb-0">Bitte HVB-Größe in Schritt 1 wählen...</p>');
        hvbStuetzeArticles = [];
        return;
    }
    
    $.ajax({
        url: '/api/hvb-stuetze-articles/',
        method: 'POST',
        data: JSON.stringify({
            hvb_size: hvbSize
        }),
        contentType: 'application/json',
        success: function(data) {
            hvbStuetzeArticles = data.articles || [];
            renderHVBStuetzeArticles();
        },
        error: function() {
            BOMConfigurator.showAlert('Fehler beim Laden der HVB Stütze Artikel.', 'danger');
            $('#hvbStuetzeArticlesList').html('<p class="text-danger text-center mb-0">Fehler beim Laden der Artikel.</p>');
        }
    });
}

function renderHVBStuetzeArticles() {
    const container = $('#hvbStuetzeArticlesList');
    
    // Hide section if no articles
    if (!hvbStuetzeArticles || hvbStuetzeArticles.length === 0) {
        container.html('<p class="text-muted text-center mb-0">Keine HVB Stütze Artikel für diese HVB-Größe verfügbar.</p>');
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table table-sm table-bordered mb-0 text-center align-middle">';
    html += '<thead><tr><th class="text-center align-middle">Artikelnummer</th><th class="text-center align-middle">Bezeichnung</th><th class="text-center align-middle">Position</th><th class="text-center align-middle">Menge</th></tr></thead>';
    html += '<tbody>';
    
    hvbStuetzeArticles.forEach(function(article) {
        // Get saved quantity or default to 1
        const savedQuantity = configurationData[`hvb_stuetze_${article.artikelnummer}`] || '1';
        html += `
            <tr class="align-middle">
                <td class="text-center align-middle"><strong>${article.artikelnummer}</strong></td>
                <td class="align-middle">${article.artikelbezeichnung}</td>
                <td class="text-center align-middle"><span class="badge bg-secondary">${article.position}</span></td>
                <td class="text-center align-middle">
                    <input type="number" 
                           class="form-control form-control-sm text-center mx-auto" 
                           style="width: 100px;" 
                           id="hvb-stuetze-qty-${article.artikelnummer}" 
                           value="${savedQuantity}" 
                           min="0" 
                           step="1"
                           onchange="saveHVBStuetzeQuantity('${article.artikelnummer}', this.value)">
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.html(html);
}

function saveHVBStuetzeQuantity(artikelnummer, quantity) {
    // Save quantity to configurationData
    configurationData[`hvb_stuetze_${artikelnummer}`] = quantity;
}

// ---- Pre-configured probe lengths (auto-fill from DB) ----
// Tracks whether the user has manually touched the Vorlauf/Rücklauf fields.
// Once the user types something, we stop overwriting their value.
let _probeLengthManualVorlauf = false;
let _probeLengthManualRuecklauf = false;

$(document).ready(function() {
    // Mark fields as manually edited when the user types in them
    $('#vorlauflengthperprobe').on('input', function() {
        if ($(this).val() !== '') {
            _probeLengthManualVorlauf = true;
        } else {
            _probeLengthManualVorlauf = false;
        }
    });
    $('#ruecklauflengthperprobe').on('input', function() {
        if ($(this).val() !== '') {
            _probeLengthManualRuecklauf = true;
        } else {
            _probeLengthManualRuecklauf = false;
        }
    });

    // Re-fetch probe lengths when any of these inputs change (they all live in step 2)
    $('#sondenanzahl, #bauform').on('change', function() {
        loadProbeLengths();
    });
});

function loadProbeLengths() {
    const schachttyp = $('#schachttyp').val() || configurationData['schachttyp'] || '';
    const hvbSize = $('#hvbSize').val() || configurationData['hvb_size'] || '';
    const bauform = $('#bauform').val() || '';
    const sondenanzahl = $('#sondenanzahl').val() || '';

    if (!schachttyp || !hvbSize || !sondenanzahl) {
        return; // Not enough data yet
    }

    $.ajax({
        url: '/api/probe-lengths/',
        method: 'POST',
        data: JSON.stringify({
            schachttyp: schachttyp,
            hvb_size: hvbSize,
            bauform: bauform,
            sondenanzahl: sondenanzahl
        }),
        contentType: 'application/json',
        success: function(data) {
            if (!data.found) {
                console.log('No pre-configured probe lengths found for this combination.');
                // Clear placeholders to show defaults
                $('#vorlauflengthperprobe').attr('placeholder', 'z.B. 0.245');
                $('#ruecklauflengthperprobe').attr('placeholder', 'z.B. 0.145');
                return;
            }

            console.log('Pre-configured probe lengths:', data);

            // Update placeholders to show the DB value so user knows what will be used
            if (data.vorlauf_laenge) {
                $('#vorlauflengthperprobe').attr('placeholder', `DB: ${data.vorlauf_laenge} m`);
            }
            if (data.ruecklauf_laenge) {
                $('#ruecklauflengthperprobe').attr('placeholder', `DB: ${data.ruecklauf_laenge} m`);
            }

            // Auto-fill ONLY if the user has NOT manually entered a value
            if (!_probeLengthManualVorlauf && data.vorlauf_laenge) {
                $('#vorlauflengthperprobe').val(data.vorlauf_laenge);
            }
            if (!_probeLengthManualRuecklauf && data.ruecklauf_laenge) {
                $('#ruecklauflengthperprobe').val(data.ruecklauf_laenge);
            }
        },
        error: function(xhr, status, error) {
            console.error('Error loading probe lengths:', error);
        }
    });
}

function updateLengthDisplays() {
    updateHvbLengthDisplay();
    updateProbeDistanceDisplay();
}

function updateHvbLengthDisplay() {
    const sondenanzahlInput = $('#sondenanzahl').val();
    const sondenanzahl = sondenanzahlInput ? parseFloat(sondenanzahlInput) : 0;
    const zuschlagLinks = parseFloat($('#zuschlagLinks').val()) || 100;
    const zuschlagRechts = parseFloat($('#zuschlagRechts').val()) || 100;
    const anschlussart = $('#anschlussart').val() || 'einseitig';
    
    // More lenient validation - allow calculation if we have valid numbers, even if sondenanzahl is 1
    if (!sondenanzahlInput || sondenanzahlInput === '' || isNaN(sondenanzahl) || sondenanzahl < 1) {
        $('#hvbLengthDisplay').text('–');
        $('#hvbLengthFormula').text('Bitte Anzahl der Sonden eingeben.');
        return;
    }
    
    // Constant value: 100 (NOT sondenabstand)
    const constant = 100;
    
    let totalMm;
    let formula;
    
    if (anschlussart === 'einseitig') {
        // Einseitig: ((X-1) * 100 + Zuschlag 1 + Zuschlag 2) * 2
        const base = (sondenanzahl - 1) * constant;
        totalMm = (base + zuschlagLinks + zuschlagRechts) * 2;
        formula = `Einseitig: ((${sondenanzahl} - 1) × 100 + ${zuschlagLinks} + ${zuschlagRechts}) × 2 = ${totalMm}mm`;
    } else if (anschlussart === 'beidseitig') {
        // Beidseitig: ((X/2 - 1) * 100 + Zuschlag 1 + Zuschlag 2) * 2
        const halfProbes = sondenanzahl / 2;
        const base = (halfProbes - 1) * constant;
        totalMm = (base + zuschlagLinks + zuschlagRechts) * 2;
        formula = `Beidseitig: ((${sondenanzahl} / 2 - 1) × 100 + ${zuschlagLinks} + ${zuschlagRechts}) × 2 = ${totalMm}mm`;
    } else {
        // Default to einseitig if unknown
        const base = (sondenanzahl - 1) * constant;
        totalMm = (base + zuschlagLinks + zuschlagRechts) * 2;
        formula = `Einseitig: ((${sondenanzahl} - 1) × 100 + ${zuschlagLinks} + ${zuschlagRechts}) × 2 = ${totalMm}mm`;
    }
    
    const totalMeters = (totalMm / 1000).toFixed(3);
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
        // Beidseitig: (je Seite Math.ceil(sondenanzahl/2) - 1) × sondenabstand
        const sondenProSeite = Math.ceil(sondenanzahl / 2);
        const effektiveSonden = Math.max(sondenProSeite - 1, 0);
        totalMm = effektiveSonden * sondenabstand;
        formula = `${sondenanzahl} Sonden, beidseitig: (je Seite ${sondenProSeite} - 1) × ${sondenabstand} mm = ${totalMm} mm`;
    } else {
        // Einseitig: (sondenanzahl - 1) × sondenabstand
        totalMm = (sondenanzahl - 1) * sondenabstand;
        formula = `${sondenanzahl} Sonden, einseitig: (${sondenanzahl} - 1) × ${sondenabstand} mm = ${totalMm} mm`;
    }
    
    const totalMeters = (totalMm / 1000).toFixed(2);
    $('#probeDistanceDisplay').text(`${totalMm} mm (${totalMeters} m)`);
    $('#probeDistanceFormula').text(formula);
}

function checkConfiguration() {
    // Collect form data
    configurationData = {
        configuration_name: $('#configName').val(),
        schachttyp: $('#schachttyp').val(),
        hvb_size: $('#hvbSize').val(),
        wp_diameter: $('#wpDiameter').val(),
        wp_diameter: $('#wpDiameter').val(),
        sonden_durchmesser: $('#sondenDurchmesser').val(),
        sondenanzahl: $('#sondenanzahl').val(),
        sondenabstand: $('#sondenabstand').val(),
        anschlussart: $('#anschlussart').val(),
        kugelhahn_type: $('#kugelhahnType').val(),
        dfm_type: $('#dfmType').val(),
        dfm_category: $('#dfmCategory').val(),
        dfm_kugelhahn_type: $('#dfmKugelhahnType').val(),
        bauform: $('#bauform').val(),
        zuschlag_links: $('#zuschlagLinks').val(),
        zuschlag_rechts: $('#zuschlagRechts').val()
    };
    
    // Check for existing configurations
    $.ajax({
        url: '/api/check-configuration/',
        method: 'POST',
        data: JSON.stringify(configurationData),
        contentType: 'application/json',
        success: function(data) {
            $('#configurationCheck').addClass('d-none');
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
        ['HVB-Größe', `${configurationData.hvb_size} mm`],
        ['Sonden-Durchmesser', `${configurationData.sonden_durchmesser} mm`],
        ['Bauform', configurationData.bauform === 'U' ? 'U-Form' : 'I-Form'],
        ['Anzahl Sonden', configurationData.sondenanzahl],
        ['Sondenabstand', `${configurationData.sondenabstand} mm`],
        ['Anschlussart', configurationData.anschlussart],
        ['Kugelhahn-Typ', configurationData.kugelhahn_type || 'Nicht ausgewählt'],
        ['DFM-Kategorie', configurationData.dfm_category || 'Nicht ausgewählt'],
        ['DFM-Typ', configurationData.dfm_type || 'Nicht ausgewählt'],
        ['D-Kugelhahn-Typ', configurationData.dfm_kugelhahn_type || 'Nicht ausgewählt']
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
    
    // When copying a configuration, always let the user enter a new article number
    const isCopy = !!(window.initialConfigurationData && Object.keys(window.initialConfigurationData).length > 0);

    if (data.exists && !isCopy) {
        if (data.type === 'full_configuration') {
            statusClass = 'status-existing';
            statusText = 'Bestehende Konfiguration';
            html = `
                <div class="alert alert-success">
                    <div class="d-flex align-items-center justify-content-between gap-2">
                        <h6 class="mb-0"><i class="fas fa-check-circle me-2"></i>Konfiguration bereits vorhanden</h6>
                        <span class="status-badge ${statusClass}">${statusText}</span>
                    </div>
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
                    <div class="d-flex align-items-center justify-content-between gap-2">
                        <h6 class="mb-0"><i class="fas fa-exclamation-triangle me-2"></i>Mutterartikel gefunden</h6>
                        <span class="status-badge ${statusClass}">${statusText}</span>
                    </div>
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
        statusText = isCopy ? 'Kopie' : 'Neue Konfiguration';

        // When copying, check if the original article had a mother-child pattern (e.g. 1000784-018)
        let prefillValue = '';
        let prefillHint = '';
        if (isCopy) {
            const origArticle = window.initialConfigurationData.full_article_number || '';
            const motherChildMatch = origArticle.match(/^(\d{5,})-(\d+)$/);
            if (motherChildMatch) {
                prefillValue = motherChildMatch[1] + '-';
                prefillHint = `Mutterartikel <code>${motherChildMatch[1]}</code> aus Originalkonfiguration. Bitte Kindnummer eingeben.`;
            }
        }

        html = `
            <div class="article-number-panel">
                <div class="article-number-panel__header">
                    <h6><i class="fas fa-plus-circle me-2"></i>${statusText}</h6>
                    <span class="status-badge ${statusClass}">${statusText}</span>
                </div>
                <p class="mb-3">${data.message}</p>
                <div class="mb-0">
                    <label class="form-label">Neue Artikelnummer:</label>
                    <input type="text" class="form-control" id="newArticleNumber" 
                           value="${prefillValue}"
                           placeholder="z.B. 1000089-001" required>
                    ${prefillHint ? `<small class="form-text text-muted">${prefillHint}</small>` : ''}
                </div>
            </div>
        `;
    }
    $('#articleNumberContent').html(html);
    
    // When user edits the new article number, clear any previous duplicate-warning state
    const $newArticleInput = $('#newArticleNumber');
    if ($newArticleInput.length) {
        $newArticleInput.on('input change', function () {
            $(this).removeClass('is-invalid');
            $(this).next('.invalid-feedback').remove();
        });
    }
}

function generateBOM() {
    const generateBtn = $('#generateBomBtn');
    BOMConfigurator.showLoading(generateBtn);
    
    // Save all step data before generating BOM
    saveStepData(1);
    saveStepData(2);
    saveStepData(3);
    saveStepData(4);
    
    // Refresh dynamic fields before sending
    configurationData.dfm_category = $('#dfmCategory').val();
    configurationData.dfm_type = $('#dfmType').val();
    configurationData.dfm_kugelhahn_type = $('#dfmKugelhahnType').val();
    configurationData.kugelhahn_type = $('#kugelhahnType').val();
    configurationData.bauform = $('#bauform').val();
    
    // Debug logging
    console.log('DEBUG BOM Generation - Sending data:', {
        kugelhahn_type: configurationData.kugelhahn_type,
        dfm_category: configurationData.dfm_category,
        dfm_type: configurationData.dfm_type,
        dfm_kugelhahn_type: configurationData.dfm_kugelhahn_type
    });
    
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
    
    // Add HVB Stuetze articles with custom quantities
    if (hvbStuetzeArticles.length > 0) {
        configurationData.hvb_stuetze_articles = {};
        hvbStuetzeArticles.forEach(function(article) {
            const quantityInput = $(`#hvb-stuetze-qty-${article.artikelnummer}`);
            if (quantityInput.length) {
                const quantity = quantityInput.val();
                if (quantity && parseFloat(quantity) > 0) {
                    configurationData.hvb_stuetze_articles[article.artikelnummer] = parseFloat(quantity);
                }
            } else {
                // Fallback to saved quantity or default 1
                const savedQuantity = configurationData[`hvb_stuetze_${article.artikelnummer}`] || '1';
                configurationData.hvb_stuetze_articles[article.artikelnummer] = parseFloat(savedQuantity);
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
            let errorCode = '';
            
            if (xhr.responseJSON) {
                if (xhr.responseJSON.message) {
                    errorMessage = xhr.responseJSON.message;
                } else if (xhr.responseJSON.error) {
                    errorMessage = `Fehler: ${xhr.responseJSON.error}`;
                }
                errorCode = xhr.responseJSON.error || '';
            } else if (xhr.responseText) {
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    errorMessage = errorData.message || errorData.error || errorMessage;
                    errorCode = errorData.error || '';
                } catch (e) {
                    errorMessage = `Fehler: ${xhr.status} ${xhr.statusText}`;
                }
            }
            
            console.error('BOM Generation Error:', xhr.responseJSON || xhr.responseText);
            BOMConfigurator.showAlert(errorMessage, 'danger');
            
            // Show inline warning inside the "Neue Konfiguration" card if article number is duplicate
            if (errorCode === 'Artikelnummer bereits vergeben' || errorMessage.includes('Artikelnummer') ) {
                const $newArticleInput = $('#newArticleNumber');
                if ($newArticleInput.length) {
                    $newArticleInput.addClass('is-invalid');
                    
                    // Remove any previous feedback to avoid duplicates
                    $newArticleInput.next('.invalid-feedback').remove();
                    
                    const inlineMessage = xhr.responseJSON && xhr.responseJSON.message
                        ? xhr.responseJSON.message
                        : 'Diese Artikelnummer wird bereits verwendet. Bitte wählen Sie eine andere Artikelnummer.';
                    
                    $newArticleInput.after(
                        `<div class="invalid-feedback d-block">${inlineMessage}</div>`
                    );
                }
            }
        }
    });
}

function showBOMResult(data) {
    // Ensure all data is saved
    saveStepData(1);
    saveStepData(2);
    saveStepData(3);
    
    // Get summaries for all steps
    const step1Summary = getStepSummary(1);
    const step2Summary = getStepSummary(2);
    const step3Summary = getStepSummary(3);
    
    // Debug logging
    console.log('Configuration Data:', configurationData);
    console.log('Step 1 Summary:', step1Summary);
    console.log('Step 2 Summary:', step2Summary);
    console.log('Step 3 Summary:', step3Summary);
    
    let html = `
        <div class="alert alert-success">
            <h6><i class="fas fa-check-circle me-2"></i>BOM erfolgreich generiert</h6>
            <p><strong>Konfiguration:</strong> ${configurationData.configuration_name}</p>
            <p><strong>Artikelnummer:</strong> <code>${data.article_number}</code></p>
        </div>
        
        <!-- Configuration Summary -->
        <div class="card mb-4">
            <div class="card-header">
                <h6 class="mb-0"><i class="fas fa-info-circle me-2"></i>Konfigurationsübersicht</h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <div class="summary-section">
                            <h6 class="text-muted mb-2"><i class="fas fa-info-circle me-2"></i>Schritt 1: Schachttyp & HVB</h6>
                            <div class="previous-steps-summary">
                                <table class="table table-sm table-borderless mb-0">
                                    <tbody>
    `;
    
    // Add Step 1 summary
    step1Summary.forEach(function(row) {
        html += `
                                        <tr>
                                            <td>${row[0]}:</td>
                                            <td><strong>${row[1]}</strong></td>
                                        </tr>
        `;
    });
    
    html += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="summary-section">
                            <h6 class="text-muted mb-2"><i class="fas fa-info-circle me-2"></i>Schritt 2: Sonden-Konfiguration</h6>
                            <div class="previous-steps-summary">
                                <table class="table table-sm table-borderless mb-0">
                                    <tbody>
    `;
    
    // Add Step 2 summary
    step2Summary.forEach(function(row) {
        html += `
                                        <tr>
                                            <td>${row[0]}:</td>
                                            <td><strong>${row[1]}</strong></td>
                                        </tr>
        `;
    });
    
    html += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
                
                ${step3Summary.length > 0 ? `
                <div class="row">
                    <div class="col-md-12">
                        <div class="summary-section">
                            <h6 class="text-muted mb-2"><i class="fas fa-info-circle me-2"></i>Schritt 3: Zusätzliche Komponenten</h6>
                            <div class="previous-steps-summary">
                                <table class="table table-sm table-borderless mb-0">
                                    <tbody>
                ` : ''}
    
    ${step3Summary.map(function(row) {
        return `
                                        <tr>
                                            <td>${row[0]}:</td>
                                            <td><strong>${row[1]}</strong></td>
                                        </tr>
        `;
    }).join('')}
    
    ${step3Summary.length > 0 ? `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
                ` : ''}
            </div>
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
        
        // Keep standard table styling (no finalized highlighting)
        const rowClass = '';
        const rowStyle = '';
        
        html += `
            <tr class="${rowClass}" style="${rowStyle}">
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
        
        <div class="d-flex justify-content-end align-items-center mt-4 flex-wrap gap-2">
            <button type="button" class="btn btn-outline-secondary" onclick="goBackFromBom()">
                <i class="fas fa-arrow-left me-2"></i>Zurück
            </button>
            <a href="/configuration/${data.configuration_id}/" class="btn btn-primary">
                <i class="fas fa-eye me-2"></i>Konfiguration anzeigen
            </a>
            <button type="button" class="btn btn-outline-primary" onclick="exportBOM()">
                <i class="fas fa-file-csv me-2"></i>CSV exportieren
            </button>
            <a href="/configurator/" class="btn btn-outline-secondary">
                <i class="fas fa-plus me-2"></i>Neue Konfiguration
            </a>
        </div>
    `;
    
    $('#bomResult').html(html);
    // Store configuration id and article number globally so CSV export button can use them
    window.latestConfigurationId = data.configuration_id;
    window.latestArticleNumber = data.article_number || null;
}

// CSV-Export: gleiche Logik wie auf der Detailseite (clientseitiger CSV-Download)
function exportBOM() {
    const table = document.querySelector('.bom-table table');
    if (!table) {
        console.warn('Keine BOM-Tabelle für CSV-Export gefunden.');
        return;
    }

    let csv = [];

    // Headerzeile
    const headers = ['Artikelnummer', 'Menge', 'Artikelbeschreibung'];
    csv.push(headers.join(';'));

    // Spalten: [Pos. (0), Artikelnummer (1), Artikelbezeichnung (2), Menge (3), Quelle (4)]
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const cells = Array.from(row.querySelectorAll('td'));
        let artikelnummer = '';
        let menge = '';
        let artikelbezeichnung = '';

        if (cells.length > 1) {
            artikelnummer = (cells[1].textContent || '').trim();
        }
        if (cells.length > 2) {
            artikelbezeichnung = (cells[2].textContent || '').trim();
        }
        if (cells.length > 3) {
            // Rohtext aus Mengenspalte (erste Zeile, ohne "berechnet"-Info)
            menge = (cells[3].textContent || '').trim().split('\n')[0].trim();

            // Zahl normalisieren ('.' oder ',' als Dezimaltrenner)
            let mengeNumber = parseFloat(
                menge
                    .replace(/\s/g, '')
                    .replace(/[^\d,.-]/g, '')
                    .replace(/,/g, '.')
            );

            if (!isNaN(mengeNumber)) {
                // In deutsches Format mit Komma als Dezimaltrenner umwandeln
                menge = mengeNumber.toString().replace('.', ',');
            }
        }

        const rowValues = [artikelnummer, menge, artikelbezeichnung];
        csv.push(rowValues.join(';'));
    });

    const csvContent = csv.join('\r\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    // Prefer the chosen article number for the filename
    let articleNumber = (window.latestArticleNumber || configurationData.full_article_number || '').trim();
    if (!articleNumber) {
        articleNumber = 'ohne_artikelnummer';
    }
    // Sanitize for filename (no spaces/slashes)
    articleNumber = articleNumber.replace(/[^\w\-]+/g, '_');
    link.download = `${articleNumber}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Go back from BOM output (Step 5) to Step 4.
// If a temporary configuration was just created, delete it first so that
// the same article number can be reused for the corrected configuration.
function goBackFromBom() {
    const configId = window.latestConfigurationId;
    
    if (configId) {
        $.ajax({
            url: '/api/delete-configurations/',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ config_ids: [configId] }),
            complete: function() {
                // Regardless of success or failure, go back to step 4.
                window.latestConfigurationId = null;
                
                // Clear any old validation state on the article number field
                const $newArticleInput = $('#newArticleNumber');
                if ($newArticleInput.length) {
                    $newArticleInput.removeClass('is-invalid');
                    $newArticleInput.next('.invalid-feedback').remove();
                }
                
                previousStep(4);
            }
        });
    } else {
        // Fallback: just go back if we don't know the configuration ID.
        const $newArticleInput = $('#newArticleNumber');
        if ($newArticleInput.length) {
            $newArticleInput.removeClass('is-invalid');
            $newArticleInput.next('.invalid-feedback').remove();
        }
        previousStep(4);
    }
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
