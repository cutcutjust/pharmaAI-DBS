/**
 * 智药AI系统主JavaScript文件
 * PharmaAI-DBS Main JavaScript
 */

(function() {
    'use strict';

    // 当DOM加载完成后执行
    document.addEventListener('DOMContentLoaded', function() {
        console.log('智药AI系统前端已加载');
        
        // 初始化所有组件
        initTooltips();
        initPopovers();
        initAlertAutoClose();
        initFormValidation();
        initTableRowClick();
        initRefreshButtons();
    });

    /**
     * 初始化Bootstrap提示框
     */
    function initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * 初始化Bootstrap弹出框
     */
    function initPopovers() {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }

    /**
     * 自动关闭提示消息
     */
    function initAlertAutoClose() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            setTimeout(function() {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000); // 5秒后自动关闭
        });
    }

    /**
     * 表单验证
     */
    function initFormValidation() {
        const forms = document.querySelectorAll('.needs-validation');
        Array.prototype.slice.call(forms).forEach(function(form) {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    }

    /**
     * 表格行点击事件
     */
    function initTableRowClick() {
        const clickableRows = document.querySelectorAll('tr[data-href]');
        clickableRows.forEach(function(row) {
            row.style.cursor = 'pointer';
            row.addEventListener('click', function(e) {
                // 如果点击的是按钮或链接，不触发行点击
                if (e.target.closest('button, a')) {
                    return;
                }
                window.location.href = row.dataset.href;
            });
        });
    }

    /**
     * 初始化刷新按钮
     */
    function initRefreshButtons() {
        const refreshButtons = document.querySelectorAll('[data-action="refresh"]');
        refreshButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                location.reload();
            });
        });
    }

    /**
     * 显示加载动画
     */
    window.showLoading = function() {
        const loadingHtml = `
            <div id="globalLoading" class="position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center" 
                 style="background-color: rgba(0,0,0,0.5); z-index: 9999;">
                <div class="text-center">
                    <div class="spinner-border text-light" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                    <p class="text-light mt-2">加载中，请稍候...</p>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', loadingHtml);
    };

    /**
     * 隐藏加载动画
     */
    window.hideLoading = function() {
        const loading = document.getElementById('globalLoading');
        if (loading) {
            loading.remove();
        }
    };

    /**
     * 显示提示消息
     */
    window.showToast = function(message, type = 'info') {
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="关闭"></button>
                </div>
            </div>
        `;
        
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // 移除已关闭的toast
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });
    };

    /**
     * AJAX请求封装
     */
    window.ajaxRequest = function(url, options = {}) {
        const defaults = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const config = Object.assign({}, defaults, options);
        
        return fetch(url, config)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('请求失败:', error);
                showToast('请求失败，请重试', 'danger');
                throw error;
            });
    };

    /**
     * 格式化日期时间
     */
    window.formatDateTime = function(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    };

    /**
     * 格式化日期
     */
    window.formatDate = function(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    };

    /**
     * 确认对话框
     */
    window.confirmAction = function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    };

})();

