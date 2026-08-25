/**
 * Custom UI Dropdown Component Controller & Instant Table Filter
 */

// Inject global hover CSS for custom select & search bar
(function injectHoverStyles() {
  if (document.getElementById('custom-select-hover-styles')) return;
  const style = document.createElement('style');
  style.id = 'custom-select-hover-styles';
  style.textContent = `
    .custom-select-trigger {
      transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    .custom-select-trigger:hover {
      background-color: #f1f5f9 !important;
      border-color: #94a3b8 !important;
      box-shadow: 0 4px 12px rgba(15,23,42,0.1) !important;
    }
    .custom-select-option {
      transition: background-color 0.15s ease, color 0.15s ease !important;
    }
    .custom-select-option:hover {
      background-color: #eff6ff !important;
      color: #1d4ed8 !important;
    }
    .search-bar-container {
      transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    .search-bar-container:hover,
    .search-bar-container:focus-within {
      border-color: #94a3b8 !important;
      box-shadow: 0 4px 12px rgba(15,23,42,0.08) !important;
    }

    /* CSS Tooltip (native, no JS needed) */
    .custom-select-trigger[data-tooltip],
    .custom-select-option[data-tooltip] {
      position: relative;
    }
    .custom-select-trigger[data-tooltip]:hover::after,
    .custom-select-option[data-tooltip]:hover::after {
      content: attr(data-tooltip);
      position: absolute;
      bottom: calc(100% + 6px);
      left: 50%;
      transform: translateX(-50%);
      background: #1e293b;
      color: #fff;
      font-size: 12px;
      padding: 5px 10px;
      border-radius: 6px;
      white-space: nowrap;
      z-index: 9999;
      pointer-events: none;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .custom-select-trigger[data-tooltip]:hover::before,
    .custom-select-option[data-tooltip]:hover::before {
      content: '';
      position: absolute;
      bottom: calc(100% + 2px);
      left: 50%;
      transform: translateX(-50%);
      border: 4px solid transparent;
      border-top-color: #1e293b;
      z-index: 9999;
      pointer-events: none;
    }
  `;
  document.head.appendChild(style);
})();

// 1. Custom UI Select Component Controller
document.addEventListener('DOMContentLoaded', function() {
  function initCustomSelects() {
    document.querySelectorAll('.custom-select-wrapper').forEach(wrapper => {
      if (wrapper.dataset.initialized === 'true') return;
      wrapper.dataset.initialized = 'true';

      const trigger = wrapper.querySelector('.custom-select-trigger');
      const menu = wrapper.querySelector('.custom-select-menu');
      const arrow = wrapper.querySelector('.custom-select-arrow');
      const hiddenSelect = wrapper.querySelector('.custom-select-hidden');
      const labelSpan = wrapper.querySelector('.custom-select-label');
      const options = wrapper.querySelectorAll('.custom-select-option');
      const searchInput = wrapper.querySelector('.custom-select-search');
      const isAutoSubmit = wrapper.dataset.autoSubmit === 'true';

      if (!trigger || !menu || !hiddenSelect) return;

      // Set initial tooltip
      if (labelSpan) trigger.setAttribute('data-tooltip', 'Selected: ' + labelSpan.textContent.trim());

      // Prevent clicks inside the dropdown menu from bubbling to document (which closes all menus)
      menu.addEventListener('click', (e) => e.stopPropagation());

      // Toggle Menu
      trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = !menu.classList.contains('d-none');
        
        // Close all other open custom select menus first
        document.querySelectorAll('.custom-select-menu').forEach(m => m.classList.add('d-none'));
        document.querySelectorAll('.custom-select-arrow').forEach(a => a.style.transform = 'rotate(0deg)');

        if (!isOpen) {
          menu.classList.remove('d-none');
          if (arrow) arrow.style.transform = 'rotate(180deg)';
          if (searchInput) {
            searchInput.value = '';
            options.forEach(opt => opt.style.display = '');
            setTimeout(() => searchInput.focus(), 50);
          }
        }
      });

      // Filter Options Inside Dropdown
      if (searchInput) {
        searchInput.addEventListener('input', (e) => {
          const q = e.target.value.toLowerCase().trim();
          options.forEach(opt => {
            const labelEl = opt.querySelector('.option-label');
            const text = (labelEl ? labelEl.textContent : opt.textContent).toLowerCase();
            opt.style.display = text.includes(q) ? '' : 'none';
          });
        });
        searchInput.addEventListener('click', (e) => e.stopPropagation());
        searchInput.addEventListener('keydown', (e) => e.stopPropagation());
        searchInput.addEventListener('keyup', (e) => e.stopPropagation());
      }

      // Handle Option Selection
      options.forEach(opt => {
        opt.addEventListener('click', (e) => {
          e.stopPropagation();
          const val = opt.dataset.value;
          const label = opt.dataset.label || opt.textContent.trim();

          // Update trigger label & tooltip
          if (labelSpan) labelSpan.textContent = label;
          if (trigger) trigger.setAttribute('data-tooltip', 'Selected: ' + label);

          // Update active option styling
          options.forEach(o => {
            o.classList.remove('active-option', 'bg-light', 'fw-semibold');
            const check = o.querySelector('.check-icon');
            if (check) check.classList.add('d-none');
          });
          opt.classList.add('active-option', 'bg-light', 'fw-semibold');
          const activeCheck = opt.querySelector('.check-icon');
          if (activeCheck) activeCheck.classList.remove('d-none');

          // Update hidden select & trigger change event
          if (hiddenSelect.value !== val) {
            hiddenSelect.value = val;
            hiddenSelect.dispatchEvent(new Event('change', { bubbles: true }));
          }

          // Close menu
          menu.classList.add('d-none');
          if (arrow) arrow.style.transform = 'rotate(0deg)';

          // Auto Submit Form if requested
          if (isAutoSubmit && hiddenSelect.form) {
            hiddenSelect.form.submit();
          }
        });
      });
    });
  }

  // Close menus when clicking outside
  document.addEventListener('click', () => {
    document.querySelectorAll('.custom-select-menu').forEach(m => m.classList.add('d-none'));
    document.querySelectorAll('.custom-select-arrow').forEach(a => a.style.transform = 'rotate(0deg)');
  });

  initCustomSelects();
  // Expose to window for dynamic content re-initialization
  window.initCustomSelects = initCustomSelects;
});


// 2. Universal Client-side Instant Table & Card Search Filter
window.initTableFilter = function(options) {
  const {
    inputId,
    dropdownId,
    tableId,
    rowSelector = 'tbody tr:not(.no-filter-row)',
    statusAttr = 'data-status'
  } = options;

  const searchInput = inputId ? document.getElementById(inputId) : null;
  const dropdownSelect = dropdownId ? document.getElementById(dropdownId) : null;
  const tableEl = tableId ? document.getElementById(tableId) : null;

  if (!tableEl && !document.querySelectorAll(rowSelector).length) {
    return;
  }

  function filterData() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const filterValue = dropdownSelect ? dropdownSelect.value.trim() : 'all';

    const rows = tableEl 
      ? tableEl.querySelectorAll(rowSelector)
      : document.querySelectorAll(rowSelector);

    let matchCount = 0;

    rows.forEach(row => {
      if (row.classList.contains('no-filter-row')) return;

      const text = row.textContent.toLowerCase();
      const itemStatus = (row.getAttribute(statusAttr) || row.dataset.status || '').toLowerCase().trim();
      const targetFilter = filterValue.toLowerCase();

      const textMatches = !query || text.includes(query);

      let filterMatches = true;
      if (targetFilter && targetFilter !== 'all' && targetFilter !== '') {
        if (targetFilter === 'critical') {
          filterMatches = (itemStatus === 'critical' || itemStatus === 'out of stock' || itemStatus === 'below safety');
        } else if (targetFilter === 'low') {
          filterMatches = (itemStatus === 'low' || itemStatus === 'low stock');
        } else if (targetFilter === 'normal' || targetFilter === 'adequate') {
          filterMatches = (itemStatus === 'normal' || itemStatus === 'adequate' || itemStatus === 'normal stock');
        } else if (targetFilter === 'overstock') {
          filterMatches = (itemStatus === 'overstock');
        } else if (targetFilter === 'active') {
          filterMatches = (itemStatus === 'active' || itemStatus === '1' || itemStatus === 'true');
        } else if (targetFilter === 'inactive') {
          filterMatches = (itemStatus === 'inactive' || itemStatus === '0' || itemStatus === 'false');
        } else {
          filterMatches = itemStatus.includes(targetFilter);
        }
      }

      if (textMatches && filterMatches) {
        row.style.display = '';
        matchCount++;
      } else {
        row.style.display = 'none';
      }
    });

    if (tableEl && tableEl.tagName === 'TABLE') {
      const tbody = tableEl.querySelector('tbody') || tableEl;
      let emptyRow = tbody.querySelector('.no-filter-row');

      if (matchCount === 0) {
        if (!emptyRow) {
          emptyRow = document.createElement('tr');
          emptyRow.className = 'no-filter-row text-center text-muted py-4';
          const colCount = tableEl.querySelectorAll('thead th').length || 6;
          emptyRow.innerHTML = `<td colspan="${colCount}" class="py-5 text-muted small">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="mb-2 text-secondary">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <div>No matching records found</div>
          </td>`;
          tbody.appendChild(emptyRow);
        }
        emptyRow.style.display = '';
      } else if (emptyRow) {
        emptyRow.style.display = 'none';
      }
    }
  }

  if (searchInput) {
    searchInput.addEventListener('input', filterData);
    searchInput.addEventListener('keyup', filterData);
  }

  if (dropdownSelect) {
    dropdownSelect.addEventListener('change', filterData);
  }

  filterData();
};
