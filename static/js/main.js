document.addEventListener('DOMContentLoaded', () => {
    const rawFileInput = document.getElementById('raw-file');
    const templateFileInput = document.getElementById('template-file');
    const autoMapBtn = document.getElementById('auto-map-btn');
    const transformBtn = document.getElementById('transform-btn');
    const spinner = document.getElementById('loading-spinner');
    const statusMessage = document.getElementById('status-message');
    const outputFormatSelect = document.getElementById('output-format');
    const transformFormatSelect = document.getElementById('transform-format');
    
    let currentRawFilename = null;
    let currentTemplateFilename = null;

    const isDesktop = window.pywebview && window.pywebview.api && window.pywebview.api.select_file_native;

    // Synchronize both format dropdowns
    if (outputFormatSelect && transformFormatSelect) {
        outputFormatSelect.addEventListener('change', () => {
            transformFormatSelect.value = outputFormatSelect.value;
        });
        transformFormatSelect.addEventListener('change', () => {
            outputFormatSelect.value = transformFormatSelect.value;
        });
    }

    // Enable Auto-Map button only when both files are selected
    function checkFiles() {
        const hasRaw = isDesktop ? !!currentRawFilename : (rawFileInput && rawFileInput.files.length > 0);
        const hasTemplate = isDesktop ? !!currentTemplateFilename : (templateFileInput && templateFileInput.files.length > 0);
        
        if (hasRaw && hasTemplate) {
            autoMapBtn.disabled = false;
            autoMapBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            autoMapBtn.disabled = true;
            autoMapBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }

    if (rawFileInput) rawFileInput.addEventListener('change', checkFiles);
    if (templateFileInput) templateFileInput.addEventListener('change', checkFiles);

    // Setup native file click handlers if in desktop app
    if (isDesktop) {
        rawFileInput.addEventListener('click', (e) => e.preventDefault());
        templateFileInput.addEventListener('click', (e) => e.preventDefault());

        const rawZone = rawFileInput.closest('.upload-zone');
        const templateZone = templateFileInput.closest('.upload-zone');

        rawZone.addEventListener('click', (e) => {
            e.preventDefault();
            const sessionId = window.SESSION_ID;
            window.pywebview.api.select_file_native(sessionId, 'raw').then(result => {
                if (result.success) {
                    const nameElement = document.getElementById('raw-file-name');
                    nameElement.textContent = result.filename;
                    nameElement.classList.add('text-primary', 'font-semibold');
                    currentRawFilename = result.filename;
                    checkFiles();
                } else if (result.error !== "User cancelled the file dialog") {
                    alert("Error: " + result.error);
                }
            });
        });

        templateZone.addEventListener('click', (e) => {
            e.preventDefault();
            const sessionId = window.SESSION_ID;
            window.pywebview.api.select_file_native(sessionId, 'template').then(result => {
                if (result.success) {
                    const nameElement = document.getElementById('template-file-name');
                    nameElement.textContent = result.filename;
                    nameElement.classList.add('text-primary', 'font-semibold');
                    currentTemplateFilename = result.filename;
                    checkFiles();
                } else if (result.error !== "User cancelled the file dialog") {
                    alert("Error: " + result.error);
                }
            });
        });
    }

    // Drag & Drop Micro-interactions
    const setupDragAndDrop = (inputId) => {
        const input = document.getElementById(inputId);
        if (!input) return;
        const zone = input.closest('.upload-zone');
        if (!zone) return;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            zone.addEventListener(eventName, () => zone.classList.add('drag-active'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, () => zone.classList.remove('drag-active'), false);
        });

        zone.addEventListener('drop', (e) => {
            if (isDesktop) return; // Prevent drop in desktop app to force native workflow
            const dt = e.dataTransfer;
            if (dt.files && dt.files.length > 0) {
                input.files = dt.files;
                input.dispatchEvent(new Event('change'));
            }
        });
    };

    setupDragAndDrop('raw-file');
    setupDragAndDrop('template-file');

    autoMapBtn.addEventListener('click', async () => {
        const usernameEl = document.getElementById('username');
        const username = (usernameEl ? usernameEl.value.trim() : '') || 'Pitch Demo';

        autoMapBtn.classList.add('hidden');
        spinner.classList.remove('hidden');
        statusMessage.textContent = 'Uploading and analyzing files...';
        statusMessage.style.color = '';

        try {
            let response;
            if (isDesktop) {
                const payload = {
                    username: username,
                    raw_filename: currentRawFilename,
                    template_filename: currentTemplateFilename
                };
                response = await fetch('/upload_native', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
            } else {
                const formData = new FormData();
                formData.append('username', username);
                formData.append('raw_file', rawFileInput.files[0]);
                formData.append('template_file', templateFileInput.files[0]);

                response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
            }

            const data = await response.json();

            if (data.success) {
                currentRawFilename = data.raw_filename;
                currentTemplateFilename = data.template_filename;
                renderMappings(data);
                
                const mappingSection = document.getElementById('mapping-section');
                mappingSection.classList.remove('hidden');
                setTimeout(() => mappingSection.classList.add('animate-expand-down'), 10);
                
                statusMessage.textContent = '';
                // Enable re-mapping easily
                autoMapBtn.innerHTML = '<span class="material-symbols-outlined">refresh</span> Re-Map Fields';
                autoMapBtn.classList.remove('hidden');
            } else {
                statusMessage.textContent = `Error: ${data.error}`;
                statusMessage.style.color = 'red';
                autoMapBtn.classList.remove('hidden');
            }
        } catch (error) {
            statusMessage.textContent = `Error: ${error.message}`;
            statusMessage.style.color = 'red';
            autoMapBtn.classList.remove('hidden');
        } finally {
            spinner.classList.add('hidden');
        }
    });

    function renderMappings(data) {
        const { mappings, raw_columns, template_columns, contamination_info, data_patterns } = data;
        const mappingList = document.getElementById('mapping-list');
        mappingList.innerHTML = '';
        
        // Contamination warning
        const warningBox = document.getElementById('contamination-warning');
        if (contamination_info && Object.keys(contamination_info).length > 0) {
            warningBox.classList.remove('hidden');
            warningBox.innerHTML = `<strong>⚠️ Data Quality Issue Detected:</strong> ${Object.keys(contamination_info).length} column(s) have overlapping values. Review mappings carefully.`;
        } else {
            warningBox.classList.add('hidden');
        }

        let mappedCount = 0;
        const totalCount = Object.keys(mappings).length;

        Object.entries(mappings).forEach(([templateCol, mappingVal]) => {
            const rawCol = Array.isArray(mappingVal) ? mappingVal[0] : mappingVal;
            const confidence = Array.isArray(mappingVal) && mappingVal.length > 1 ? mappingVal[1] : (rawCol ? 1.0 : 0.0);

            if (rawCol !== null && rawCol !== '') mappedCount++;
            
            const row = document.createElement('tr');
            row.className = 'animate-fade-in-up hover:bg-surface-container-lowest transition-colors border-b border-outline-variant/50';
            row.style.animationDelay = `${Math.min(100 + (mappedCount * 50), 1000)}ms`;

            // 1. Template Column
            const tColDiv = document.createElement('td');
            tColDiv.className = 'p-4 font-semibold text-primary';
            tColDiv.textContent = templateCol;
            row.appendChild(tColDiv);

            // 2. Select Box
            const selectDiv = document.createElement('td');
            selectDiv.className = 'p-4';
            const select = document.createElement('select');
            select.className = 'mapping-select w-full bg-surface border border-outline-variant rounded p-2 text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none cursor-pointer';
            select.dataset.templateCol = templateCol;
            
            const noMatchOpt = document.createElement('option');
            noMatchOpt.value = '';
            noMatchOpt.textContent = '<No Match>';
            select.appendChild(noMatchOpt);

            raw_columns.forEach(col => {
                const opt = document.createElement('option');
                opt.value = col;
                opt.textContent = col;
                if (col === rawCol) {
                    opt.selected = true;
                }
                select.appendChild(opt);
            });
            selectDiv.appendChild(select);
            row.appendChild(selectDiv);

            // 3. Confidence Indicator
            const confDiv = document.createElement('td');
            confDiv.className = 'p-4 text-center confidence-cell';
            updateConfidenceDisplay(confDiv, rawCol, confidence, false);
            row.appendChild(confDiv);

            // 4. Data Pattern
            const patternDiv = document.createElement('td');
            patternDiv.className = 'p-4 text-right text-sm text-on-surface-variant pattern-cell';
            if (rawCol !== null && data_patterns && data_patterns[rawCol]) {
                const isContaminated = contamination_info && contamination_info[rawCol] ? '⚠️ ' : '';
                patternDiv.innerHTML = `${isContaminated}(${data_patterns[rawCol]})`;
            }
            row.appendChild(patternDiv);

            // Event listener for select changes
            select.addEventListener('change', () => {
                const selectedVal = select.value;
                if (selectedVal === '') {
                    updateConfidenceDisplay(confDiv, null, 0, true);
                    patternDiv.textContent = '';
                } else if (selectedVal === rawCol) {
                    updateConfidenceDisplay(confDiv, selectedVal, confidence, false);
                    if (data_patterns && data_patterns[selectedVal]) {
                        patternDiv.textContent = `(${data_patterns[selectedVal]})`;
                    }
                } else {
                    updateConfidenceDisplay(confDiv, selectedVal, 1.0, true);
                    if (data_patterns && data_patterns[selectedVal]) {
                        patternDiv.textContent = `(${data_patterns[selectedVal]})`;
                    }
                }
                updateMappedCount();
            });

            mappingList.appendChild(row);
        });

        document.getElementById('mapped-count').textContent = `${mappedCount}/${totalCount}`;
    }

    function updateConfidenceDisplay(el, rawCol, confidence, isManual) {
        if (!rawCol) {
            el.innerHTML = `<span class="inline-flex items-center gap-1 font-label-caps text-label-caps font-bold text-outline">⚪ N/A</span>`;
            return;
        }

        if (isManual) {
            el.innerHTML = `<span class="inline-flex items-center gap-1 font-label-caps text-label-caps font-bold text-primary">👤 Manual (100%)</span>`;
            return;
        }

        const confPct = Math.round(confidence * 100);
        let textClass = 'text-tertiary';
        let icon = '🟠';
        if (confidence >= 0.8) { textClass = 'text-success'; icon = '🟢'; }
        else if (confidence >= 0.6) { textClass = 'text-tertiary'; icon = '🟡'; }
        
        el.innerHTML = `<span class="inline-flex items-center gap-1 font-label-caps text-label-caps font-bold ${textClass}">${icon} ${confPct}%</span>`;
    }

    function updateMappedCount() {
        const selects = document.querySelectorAll('.mapping-select');
        let count = 0;
        selects.forEach(s => {
            if (s.value !== '') count++;
        });
        const total = selects.length;
        const mappedCountEl = document.getElementById('mapped-count');
        if (mappedCountEl) {
            mappedCountEl.textContent = `${count}/${total}`;
        }
    }

    transformBtn.addEventListener('click', async () => {
        // Collect adjusted mappings
        const adjustedMappings = {};
        document.querySelectorAll('.mapping-select').forEach(select => {
            const templateCol = select.dataset.templateCol;
            const selectedRawCol = select.value === '' ? null : select.value;
            adjustedMappings[templateCol] = [selectedRawCol, 1.0]; 
        });

        const outputFormat = (transformFormatSelect ? transformFormatSelect.value : (outputFormatSelect ? outputFormatSelect.value : 'excel')) || 'excel';
        const usernameEl = document.getElementById('username');
        const username = (usernameEl ? usernameEl.value.trim() : '') || 'Pitch Demo';

        const payload = {
            username: username,
            mappings: adjustedMappings,
            output_format: outputFormat,
            raw_filename: currentRawFilename,
            template_filename: currentTemplateFilename
        };

        transformBtn.disabled = true;
        const originalBtnHtml = transformBtn.innerHTML;
        transformBtn.innerHTML = '<span class="material-symbols-outlined animate-spin">sync</span> Transforming...';

        try {
            const response = await fetch('/transform', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.success) {
                const downloadSection = document.getElementById('download-section');
                downloadSection.classList.remove('hidden');
                setTimeout(() => downloadSection.classList.add('animate-expand-down'), 10);
                
                document.getElementById('total-rows').textContent = data.stats.total_rows;
                document.getElementById('total-cols').textContent = data.stats.total_columns;
                document.getElementById('completeness').textContent = data.stats.completeness.toFixed(1) + '%';
                
                const downloadLink = document.getElementById('download-link');
                downloadLink.href = data.download_url;

                // Render Live Preview Table
                if (data.preview && data.preview.columns) {
                    renderPreviewTable(data.preview);
                }

                // Scroll smoothly to the results
                downloadSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                alert(`Transformation failed: ${data.error}`);
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            transformBtn.disabled = false;
            transformBtn.innerHTML = originalBtnHtml;
        }
    });

    function renderPreviewTable(preview) {
        const thead = document.getElementById('preview-thead');
        const tbody = document.getElementById('preview-tbody');
        if (!thead || !tbody) return;

        thead.innerHTML = '';
        tbody.innerHTML = '';

        const trHead = document.createElement('tr');
        preview.columns.forEach(col => {
            const th = document.createElement('th');
            th.className = 'p-3 border-b border-outline-variant font-medium text-primary whitespace-nowrap';
            th.textContent = col;
            trHead.appendChild(th);
        });
        thead.appendChild(trHead);

        if (preview.rows.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = preview.columns.length;
            td.className = 'p-4 text-center text-outline';
            td.textContent = 'No records to display.';
            tr.appendChild(td);
            tbody.appendChild(tr);
            return;
        }

        preview.rows.forEach(row => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-surface-container-low transition-colors';
            preview.columns.forEach(col => {
                const td = document.createElement('td');
                td.className = 'p-3 border-b border-outline-variant/30 text-xs whitespace-nowrap';
                const val = row[col];
                td.textContent = (val !== null && val !== undefined && val !== '') ? String(val) : '-';
                if (val === null || val === undefined || val === '') {
                    td.classList.add('text-outline', 'italic');
                }
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }

    // Robust Download Trigger
    const downloadLink = document.getElementById('download-link');
    if (downloadLink) {
        downloadLink.addEventListener('click', async (e) => {
            if (downloadLink.getAttribute('href') === '#') return;
            
            e.preventDefault();
            const originalText = downloadLink.innerHTML;
            downloadLink.innerHTML = '<span class="material-symbols-outlined animate-spin">sync</span> Downloading...';
            let downloadSuccess = false;

            try {
                // DESKTOP NATIVE SAVE: Check if running in pywebview desktop app
                if (window.pywebview && window.pywebview.api && window.pywebview.api.save_file_native) {
                    const parts = downloadLink.getAttribute('href').split('/');
                    const filename = parts.pop();
                    const sessionId = parts.pop();
                    
                    const result = await window.pywebview.api.save_file_native(sessionId, filename);
                    
                    if (!result.success) {
                        if (result.error === "User cancelled the save dialog") {
                            downloadLink.innerHTML = originalText;
                            return;
                        }
                        throw new Error(result.error);
                    }
                    downloadSuccess = true;
                } else {
                    // BROWSER FALLBACK: Standard Blob-based download
                    const response = await fetch(downloadLink.href);
                    if (!response.ok) throw new Error('Download failed with server error: ' + response.statusText);
                    
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    
                    const parts = downloadLink.href.split('/');
                    const filename = parts[parts.length - 1];
                    
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    
                    setTimeout(() => {
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                    }, 200);
                    downloadSuccess = true;
                }
            } catch (error) {
                console.error('Download error:', error);
                alert('Could not download the file: ' + error.message);
            } finally {
                downloadLink.innerHTML = originalText;
                if (downloadSuccess) {
                    const originalBg = downloadLink.style.background;
                    downloadLink.innerHTML = '✅ Saved to Downloads';
                    downloadLink.style.background = '#28a745';
                    setTimeout(() => {
                        downloadLink.innerHTML = originalText;
                        downloadLink.style.background = originalBg;
                    }, 3000);
                }
            }
        });
    }
});
