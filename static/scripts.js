// static/scripts.js

// Variable global para el gráfico 
let weeklyChart = null;

document.addEventListener('DOMContentLoaded', function() {
    
    // MENÚ HAMBURGUESA
    const mobileToggle = document.getElementById('mobileToggle');
    const sidebar = document.getElementById('sidebar');
    if (mobileToggle && sidebar) {
        mobileToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            sidebar.classList.toggle('open');
        });
        document.addEventListener('click', function(event) {
            if (window.innerWidth <= 800 && sidebar.classList.contains('open') && 
                !sidebar.contains(event.target) && !mobileToggle.contains(event.target)) {
                sidebar.classList.remove('open');
            }
        });
    }

    // FECHA (si existe elemento)
    const fechaElemento = document.getElementById('fechaActual');
    if (fechaElemento) {
        const opciones = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const hoy = new Date().toLocaleDateString('es-ES', opciones);
        const fechaFormateada = hoy.charAt(0).toUpperCase() + hoy.slice(1);
        fechaElemento.textContent = fechaFormateada;
    }

    // Resaltar enlace activo
    const currentPath = window.location.pathname;
    const menuItems = document.querySelectorAll('.sidebar-menu .menu-item');
    menuItems.forEach(item => {
        const href = item.getAttribute('href');
        if (href === currentPath) {
            item.style.background = '#1e3a8a';
            item.style.fontWeight = 'bold';
        }
    });

    // RELOJ
    function updateDateTime() {
        const now = new Date();
        const diaNumero = document.getElementById('diaNumero');
        const mesNombre = document.getElementById('mesNombre');
        const anioActual = document.getElementById('anioActual');
        const horaActual = document.getElementById('horaActual');
        const diaSemana = document.getElementById('diaSemana');
        if (diaNumero) diaNumero.textContent = now.getDate();
        if (mesNombre) mesNombre.textContent = now.toLocaleString('es-ES', { month: 'short' }).toUpperCase();
        if (anioActual) anioActual.textContent = now.getFullYear();
        if (horaActual) horaActual.textContent = now.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        if (diaSemana) {
            let dia = now.toLocaleString('es-ES', { weekday: 'long' });
            diaSemana.textContent = dia.charAt(0).toUpperCase() + dia.slice(1);
        }
    }
    updateDateTime();
    setInterval(updateDateTime, 1000);

    // DASHBOARD
    async function loadStats() {
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) throw new Error('Error HTTP');
            const data = await res.json();
            document.getElementById('total-estudiantes').innerText = data.total_estudiantes;
            document.getElementById('asistencias-hoy').innerText = data.asistencias_hoy;
            document.getElementById('retrasos-hoy').innerText = data.retrasos_hoy;
            document.getElementById('tasa-asistencia').innerText = data.tasa_asistencia + '%';
            document.getElementById('trend-total').innerHTML = '<i class="fas fa-database"></i> Total registrados';
            document.getElementById('trend-asistencias').innerHTML = `<i class="fas fa-chart-line"></i> ${Math.round(data.tasa_asistencia)}% del total`;
            const retrasos = data.retrasos_hoy;
            const trendRetrasos = document.getElementById('trend-retrasos');
            if (retrasos === 0) {
                trendRetrasos.innerHTML = '<i class="fas fa-check-circle"></i> Sin retrasos hoy';
                trendRetrasos.style.color = '#4ade80';
            } else {
                trendRetrasos.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${retrasos} retraso(s)`;
                trendRetrasos.style.color = '#f87171';
            }
            document.getElementById('trend-tasa').innerHTML = '<i class="fas fa-percent"></i> Últimos 7 días';
        } catch (err) {
            console.error('Error cargando stats:', err);
        }
    }

    async function loadWeekly() {
        try {
            const res = await fetch('/api/weekly');
            if (!res.ok) throw new Error('Error HTTP');
            const data = await res.json();
            const ctx = document.getElementById('weeklyChart').getContext('2d');
            if (weeklyChart) weeklyChart.destroy();
            weeklyChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Asistencias',
                        data: data.data,
                        backgroundColor: '#3b82f6',
                        borderRadius: 12,
                        barPercentage: 0.6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { labels: { color: '#cbd5e1' } },
                        tooltip: { backgroundColor: '#1e293b' }
                    },
                    scales: {
                        y: {
                            grid: { color: '#2a2a2a' },
                            ticks: { color: '#94a3b8' },
                            beginAtZero: true,
                            stepSize: 1
                        },
                        x: {
                            ticks: { color: '#cbd5e1' }
                        }
                    }
                }
            });
        } catch (err) {
            console.error('Error en gráfico:', err);
        }
    }

    async function loadRecentActivity() {
        const container = document.getElementById('activity-list');
        if (!container) return;
        try {
            const res = await fetch('/api/recent-activity');
            if (!res.ok) throw new Error('Error HTTP');
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) {
                container.innerHTML = '<li class="activity-item">No hay actividad reciente</li>';
                return;
            }
            function escapeHtml(str) {
                if (!str) return '';
                return str.replace(/[&<>]/g, function(m) {
                    if (m === '&') return '&amp;';
                    if (m === '<') return '&lt;';
                    if (m === '>') return '&gt;';
                    return m;
                });
            }
            container.innerHTML = data.map(act => `
                <li class="activity-item">
                    <div class="activity-icon"><i class="fas fa-user-check"></i></div>
                    <div class="activity-detail">
                        <div class="activity-title">${escapeHtml(act.nombre)} registró entrada</div>
                        <div class="activity-time">${escapeHtml(act.tiempo)}</div>
                    </div>
                    <div class="activity-status">${escapeHtml(act.estado_texto)}</div>
                </li>
            `).join('');
        } catch (err) {
            console.error('Error actividad:', err);
            container.innerHTML = '<li class="activity-item">Error al cargar actividad</li>';
        }
    }

    if (document.getElementById('weeklyChart') && document.getElementById('total-estudiantes')) {
        loadStats();
        loadWeekly();
        loadRecentActivity();
        setInterval(() => {
            loadStats();
            loadRecentActivity();
        }, 30000);
        setInterval(() => loadWeekly(), 300000);
    }

    // CONTROL DE ALMUERZO (MODAL Y FILTROS)
    // Solo si estamos en la página de listado de asistencias
    if (document.getElementById('asistenciaTable')) {
        //  Modal
        let currentRowId = null;
        const modal = document.getElementById('modalAlmuerzo');
        const inputSalida = document.getElementById('modalSalida');
        const inputRegreso = document.getElementById('modalRegreso');
        const btnGuardar = document.getElementById('guardarAlmuerzo');
        const btnCancelar = document.getElementById('cancelarAlmuerzo');

        if (modal) {
            document.querySelectorAll('.btn-editar-almuerzo').forEach(btn => {
                btn.addEventListener('click', () => {
                    currentRowId = btn.getAttribute('data-id');
                    inputSalida.value = btn.getAttribute('data-salida');
                    inputRegreso.value = btn.getAttribute('data-regreso');
                    modal.style.display = 'flex';
                });
            });

            function cerrarModal() {
                modal.style.display = 'none';
                currentRowId = null;
                inputSalida.value = '';
                inputRegreso.value = '';
            }
            btnCancelar.addEventListener('click', cerrarModal);

            btnGuardar.addEventListener('click', async () => {
                const salida = inputSalida.value;
                const regreso = inputRegreso.value;
                if (!currentRowId) return;

                try {
                    const response = await fetch(`/editar_almuerzo/${currentRowId}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            hora_salida_almuerzo: salida,
                            hora_regreso_almuerzo: regreso
                        })
                    });
                    const data = await response.json();
                    if (data.success) {
                        const row = document.getElementById(`row-${currentRowId}`);
                        if (row) {
                            row.querySelector('.almuerzo-salida').innerText = salida || '--:--';
                            row.querySelector('.almuerzo-regreso').innerText = regreso || '--:--';
                            const btn = row.querySelector('.btn-editar-almuerzo');
                            if (btn) {
                                btn.setAttribute('data-salida', salida);
                                btn.setAttribute('data-regreso', regreso);
                            }
                        }
                        cerrarModal();
                    } else {
                        alert('Error al guardar: ' + (data.error || 'desconocido'));
                    }
                } catch (err) {
                    alert('Error de conexión');
                }
            });
        }

        // ---- Filtros simplificados (sin campos de almuerzo) ----
        const filterName = document.getElementById('filterName');
        const filterStatus = document.getElementById('filterStatus');
        const filterDate = document.getElementById('filterDate');
        const clearBtn = document.getElementById('clearFilters');
        const resultCountSpan = document.getElementById('filterResultCount');
        const table = document.getElementById('asistenciaTable');
        const tbody = table.querySelector('tbody');
        let rows = Array.from(tbody.querySelectorAll('tr')).filter(row => row.id !== 'noDataRow');

        function normalizeText(str) {
            return str.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        }

        function applyFilters() {
            const nameValue = normalizeText(filterName.value);
            const statusValue = filterStatus.value;
            const dateValue = filterDate.value;
            let visibleCount = 0;

            rows.forEach(row => {
                const nombre = normalizeText(row.cells[0].textContent);
                const apellido = normalizeText(row.cells[1].textContent);
                const fechaRow = row.getAttribute('data-fecha') || row.cells[2].textContent;
                const estadoRow = row.getAttribute('data-estado') || '';

                let matches = true;
                if (nameValue !== '') {
                    const fullName = nombre + ' ' + apellido;
                    if (!fullName.includes(nameValue)) matches = false;
                }
                if (matches && statusValue !== 'all') {
                    if (estadoRow !== statusValue) matches = false;
                }
                if (matches && dateValue !== '') {
                    if (fechaRow !== dateValue) matches = false;
                }

                if (matches) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            });

            const noDataMsg = tbody.querySelector('#noDataRow');
            if (visibleCount === 0 && !noDataMsg) {
                const emptyRow = document.createElement('tr');
                emptyRow.id = 'noDataRow';
                emptyRow.innerHTML = '<td colspan="8">🔍 No hay registros que coincidan con los filtros.</td>';
                tbody.appendChild(emptyRow);
            } else if (visibleCount > 0 && noDataMsg) {
                noDataMsg.remove();
            }

            if (resultCountSpan) {
                resultCountSpan.textContent = `Mostrando ${visibleCount} de ${rows.length} registros`;
            }
        }

        function clearFilters() {
            filterName.value = '';
            filterStatus.value = 'all';
            filterDate.value = '';
            applyFilters();
        }

        if (filterName) {
            filterName.addEventListener('input', applyFilters);
            filterStatus.addEventListener('change', applyFilters);
            filterDate.addEventListener('change', applyFilters);
            if (clearBtn) clearBtn.addEventListener('click', clearFilters);
            applyFilters();
        }

        // ---- Exportar a Excel (incluye columnas de almuerzo) ----
        const exportBtn = document.getElementById('exportExcelBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', function() {
                const visibleRows = Array.from(tbody.querySelectorAll('tr')).filter(row => {
                    return row.style.display !== 'none' && row.id !== 'noDataRow';
                });
                if (visibleRows.length === 0) {
                    alert('No hay datos visibles para exportar.');
                    return;
                }
                const headers = ['Nombre', 'Apellido', 'Fecha', 'Hora Entrada', 'Hora Salida', 'Estado', 'Salida Almuerzo', 'Regreso Almuerzo'];
                const data = visibleRows.map(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 8) return null;
                    return [
                        cells[0].innerText.trim(),
                        cells[1].innerText.trim(),
                        cells[2].innerText.trim(),
                        cells[3].innerText.trim(),
                        cells[4].innerText.trim(),
                        cells[5].innerText.trim(),
                        cells[6].innerText.trim(),
                        cells[7].innerText.trim()
                    ];
                }).filter(row => row !== null);
                const csvContent = [
                    headers.join(','),
                    ...data.map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(','))
                ].join('\n');
                const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', 'asistencias_filtradas.csv');
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            });
        }
    }
});