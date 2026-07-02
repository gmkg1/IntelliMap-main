document.addEventListener('DOMContentLoaded', () => {
    const rawFileInput = document.getElementById('raw-file');
    const templateFileInput = document.getElementById('template-file');
    const autoMapBtn = document.getElementById('auto-map-btn');
    const transformBtn = document.getElementById('transform-btn');
    const spinner = document.getElementById('loading-spinner');
    const statusMessage = document.getElementById('status-message');
    
    let currentRawFilename = null;
    let currentTemplateFilename = null;

    const isDesktop = window.pywebview && window.pywebview.api && window.pywebview.api.select_file_native;

    // Enable Auto-Map button only when both files are selected
    function checkFiles() {
        const hasRaw = isDesktop ? !!currentRawFilename : rawFileInput.files.length > 0;
        const hasTemplate = isDesktop ? !!currentTemplateFilename : templateFileInput.files.length > 0;
        
        if (hasRaw && hasTemplate) {
            autoMapBtn.disabled = false;
        } else {
            autoMapBtn.disabled = true;
        }
    }

    rawFileInput.addEventListener('change', checkFiles);
    templateFileInput.addEventListener('change', checkFiles);

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
        const zone = input.closest('.upload-zone');
        
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
        const username = document.getElementById('username').value.trim();
        if (!username) {
            alert('Please enter your Name / User ID for the audit logs.');
            return;
        }

        autoMapBtn.classList.add('hidden');
        spinner.classList.remove('hidden');
        statusMessage.textContent = 'Uploading and analyzing files...';

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
                // Tiny delay to ensure browser registers un-hide before animating
                setTimeout(() => mappingSection.classList.add('animate-expand-down'), 10);
                
                statusMessage.textContent = '';
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
        if (Object.keys(contamination_info).length > 0) {
            warningBox.classList.remove('hidden');
            warningBox.innerHTML = `<strong>⚠️ Data Quality Issue Detected:</strong> ${Object.keys(contamination_info).length} column(s) have overlapping values. Review mappings carefully.`;
        } else {
            warningBox.classList.add('hidden');
        }

        let mappedCount = 0;
        const totalCount = Object.keys(mappings).length;

        Object.entries(mappings).forEach(([templateCol, [rawCol, confidence]]) => {
            if (rawCol !== null) mappedCount++;
            
            const row = document.createElement('tr');
            row.className = 'animate-fade-in-up hover:bg-surface-container-lowest transition-colors border-b border-outline-variant/50';
            // Stagger rows
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
            select.className = 'mapping-select w-full bg-surface border border-outline-variant rounded p-2 text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none';
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

            // 3. Confidence
            const confDiv = document.createElement('td');
            confDiv.className = 'p-4 text-center';
            if (rawCol !== null && confidence > 0) {
                const confPct = Math.round(confidence * 100);
                let textClass = 'text-tertiary';
                let icon = '🟠';
                if (confidence >= 0.8) { textClass = 'text-success'; icon = '🟢'; }
                else if (confidence >= 0.6) { textClass = 'text-tertiary'; icon = '🟡'; }
                
                confDiv.innerHTML = `<span class="inline-flex items-center gap-1 font-label-caps text-label-caps font-bold ${textClass}">${icon} ${confPct}%</span>`;
            } else {
                confDiv.innerHTML = `<span class="inline-flex items-center gap-1 font-label-caps text-label-caps font-bold text-outline">⚪ N/A</span>`;
            }
            row.appendChild(confDiv);

            // 4. Data Pattern
            const patternDiv = document.createElement('td');
            patternDiv.className = 'p-4 text-right text-sm text-on-surface-variant';
            if (rawCol !== null && data_patterns[rawCol]) {
                const isContaminated = contamination_info[rawCol] ? '⚠️ ' : '';
                patternDiv.innerHTML = `${isContaminated}(${data_patterns[rawCol]})`;
            }
            row.appendChild(patternDiv);

            // Event listener for select changes to update count
            select.addEventListener('change', () => {
                updateMappedCount();
            });

            mappingList.appendChild(row);
        });

        document.getElementById('mapped-count').textContent = `${mappedCount}/${totalCount}`;
    }

    function updateMappedCount() {
        const selects = document.querySelectorAll('.mapping-select');
        let count = 0;
        selects.forEach(s => {
            if (s.value !== '') count++;
        });
        const total = selects.length;
        document.getElementById('mapped-count').textContent = `${count}/${total}`;
    }

    transformBtn.addEventListener('click', async () => {
        // Collect adjusted mappings
        const adjustedMappings = {};
        document.querySelectorAll('.mapping-select').forEach(select => {
            const templateCol = select.dataset.templateCol;
            const selectedRawCol = select.value === '' ? null : select.value;
            // Send back the adjusted mapping. Confidence score isn't strictly needed for transform, just the column name.
            adjustedMappings[templateCol] = [selectedRawCol, 1.0]; 
        });

        const outputFormat = document.getElementById('output-format').value;
        const username = document.getElementById('username').value.trim();

        const payload = {
            username: username,
            mappings: adjustedMappings,
            output_format: outputFormat,
            raw_filename: currentRawFilename,
            template_filename: currentTemplateFilename
        };

        transformBtn.disabled = true;
        transformBtn.textContent = 'Transforming...';

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
            } else {
                alert(`Transformation failed: ${data.error}`);
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            transformBtn.disabled = false;
            transformBtn.textContent = '✨ Transform Data';
        }
    });

    // Robust Download Trigger for Desktop Webviews
    const downloadLink = document.getElementById('download-link');
    if (downloadLink) {
        downloadLink.addEventListener('click', async (e) => {
            // If the href is just #, let it be (initial state)
            if (downloadLink.getAttribute('href') === '#') return;
            
            e.preventDefault();
            const originalText = downloadLink.innerHTML;
            downloadLink.innerHTML = '<span class="material-symbols-outlined animate-spin">sync</span> Downloading...';
            
            try {
                // DESKTOP NATIVE SAVE: Check if running in pywebview desktop app
                if (window.pywebview && window.pywebview.api && window.pywebview.api.save_file_native) {
                    // Extract session_id and filename from the href: /download/<session_id>/<filename>
                    const parts = downloadLink.getAttribute('href').split('/');
                    const filename = parts.pop();
                    const sessionId = parts.pop();
                    
                    const result = await window.pywebview.api.save_file_native(sessionId, filename);
                    
                    if (!result.success) {
                        // If it's just a cancellation, don't show an error but stop the success feedback
                        if (result.error === "User cancelled the save dialog") {
                            downloadLink.innerHTML = originalText;
                            return;
                        }
                        throw new Error(result.error);
                    }
                    
                    // Success! Proceed to finally block for visual feedback
                } else {
                    // BROWSER FALLBACK: Standard Blob-based download
                    const response = await fetch(downloadLink.href);
                    if (!response.ok) throw new Error('Download failed');
                    
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
                    }, 100);
                }
            } catch (error) {
                console.error('Download error:', error);
                alert('Could not download the file. Please check your connection and try again.');
            } finally {
                downloadLink.innerHTML = originalText;
                // Show a quick success message if no error occurred
                if (!e.defaultPrevented || downloadLink.innerHTML === originalText) {
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
