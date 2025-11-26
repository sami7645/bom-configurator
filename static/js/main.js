// Main JavaScript for BOM Configurator

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // Smooth scrolling for anchor links
    $('a[href^="#"]').on('click', function(event) {
        var target = $(this.getAttribute('href'));
        if( target.length ) {
            event.preventDefault();
            $('html, body').stop().animate({
                scrollTop: target.offset().top - 100
            }, 1000);
        }
    });

    // Form validation enhancement
    $('form').on('submit', function() {
        $(this).find('button[type="submit"]').prop('disabled', true).html(
            '<span class="loading-spinner me-2"></span>Verarbeitung...'
        );
    });

    // Number input validation
    $('input[type="number"]').on('input', function() {
        var min = parseInt($(this).attr('min'));
        var max = parseInt($(this).attr('max'));
        var value = parseInt($(this).val());
        
        if (min && value < min) {
            $(this).addClass('is-invalid');
        } else if (max && value > max) {
            $(this).addClass('is-invalid');
        } else {
            $(this).removeClass('is-invalid').addClass('is-valid');
        }
    });

    // Dynamic form field updates
    $('.form-control, .form-select').on('change', function() {
        $(this).removeClass('is-invalid is-valid');
        if ($(this).val()) {
            $(this).addClass('is-valid');
        }
    });
});

// Utility functions
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-info-circle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insert at the top of main content
    $('main .container-fluid').prepend(alertHtml);
    
    // Auto-hide after 5 seconds
    setTimeout(function() {
        $('.alert').first().fadeOut('slow', function() {
            $(this).remove();
        });
    }, 5000);
}

function formatNumber(num, decimals = 2) {
    const value = parseFloat(num);
    if (isNaN(value)) {
        return '0';
    }
    
    // If the value is a whole number, show it without decimals
    if (value % 1 === 0) {
        return value.toString();
    }
    
    // For decimal numbers, format with specified decimals
    // Remove trailing zeros and replace . with , for German format
    let formatted = value.toFixed(decimals);
    // Remove trailing zeros
    formatted = formatted.replace(/\.?0+$/, '');
    // Replace . with , for German decimal separator
    formatted = formatted.replace('.', ',');
    
    return formatted;
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('de-DE', {
        style: 'currency',
        currency: 'EUR'
    }).format(amount);
}

// Loading state management
function showLoading(element) {
    const $element = $(element);
    $element.prop('disabled', true);
    const originalText = $element.text();
    $element.data('original-text', originalText);
    $element.html('<span class="loading-spinner me-2"></span>Laden...');
}

function hideLoading(element) {
    const $element = $(element);
    $element.prop('disabled', false);
    const originalText = $element.data('original-text') || 'Absenden';
    $element.html(originalText);
}

// CSRF token helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Setup CSRF token for AJAX requests
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
});

// Export functions for global use
window.BOMConfigurator = {
    showAlert: showAlert,
    formatNumber: formatNumber,
    formatCurrency: formatCurrency,
    showLoading: showLoading,
    hideLoading: hideLoading,
    getCookie: getCookie
};
