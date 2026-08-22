let editor;
let currentCode = '';

document.addEventListener('DOMContentLoaded', function() {
    editor = CodeMirror.fromTextArea(document.getElementById('code-editor'), {
        mode: 'python',
        theme: 'monokai',
        lineNumbers: true,
        tabSize: 4,
        indentUnit: 4,
        lineWrapping: true
    });
    
    editor.on('change', function() {
        currentCode = editor.getValue();
    });
    
    currentCode = editor.getValue();
});

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;
    
    input.value = '';
    addMessage('user', message);
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: [{ role: 'user', content: message }] })
        });
        
        const data = await response.json();
        addMessage('bot', data.response);
    } catch (error) {
        addMessage('bot', '连接失败，请稍后重试。');
    }
}

function addMessage(role, content) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = role === 'user' ? 'user-message' : 'bot-message';
    
    const avatar = document.createElement('span');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (content.includes('```')) {
        content = content.replace(/```(\w+)?\n/g, '<pre><code>').replace(/```/g, '</code></pre>');
        contentDiv.innerHTML = content;
    } else {
        contentDiv.textContent = content;
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function generateCode() {
    const prompt = prompt('请输入代码生成需求：');
    if (!prompt) return;
    
    addMessage('user', `🔧 生成代码: ${prompt}`);
    
    try {
        const response = await fetch('/api/code/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt, language: 'python' })
        });
        
        const data = await response.json();
        editor.setValue(data.code.replace(/```python\n?/g, '').replace(/```\n?/g, ''));
        addMessage('bot', `代码已生成，已填充到编辑器中。\n\n${data.code}`);
    } catch (error) {
        addMessage('bot', '代码生成失败，请稍后重试。');
    }
}

async function analyzeCode() {
    const code = editor.getValue();
    if (!code.trim()) {
        addMessage('bot', '请先在编辑器中输入代码。');
        return;
    }
    
    addMessage('user', '📊 分析当前代码复杂度');
    
    try {
        const response = await fetch('/api/code/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        
        const data = await response.json();
        
        let result = '**代码分析结果：**\n\n';
        if (data.complexity.success) {
            const c = data.complexity.data;
            result += `- 代码行数 (LOC): ${c.loc}\n`;
            result += `- 函数数量: ${c.functions}\n`;
            result += `- 类数量: ${c.classes}\n`;
            result += `- 圈复杂度: ${c.cyclomatic_complexity}\n`;
            result += `- 嵌套循环数: ${c.nested_loops}\n`;
            result += `- 最深嵌套层级: ${c.deepest_nesting}\n`;
            
            if (c.cyclomatic_complexity > 10) {
                result += '\n⚠️ 警告：圈复杂度较高，建议重构。';
            }
        } else {
            result += `分析失败: ${data.complexity.error}\n`;
        }
        
        if (data.errors && data.errors.length > 0) {
            result += '\n**检测到的问题：**\n';
            data.errors.forEach((error, index) => {
                result += `${index + 1}. [行 ${error.line}] ${error.message}\n`;
            });
        } else {
            result += '\n✅ 未检测到语法错误。';
        }
        
        addMessage('bot', result);
    } catch (error) {
        addMessage('bot', '代码分析失败，请稍后重试。');
    }
}

async function optimizeCode() {
    const code = editor.getValue();
    if (!code.trim()) {
        addMessage('bot', '请先在编辑器中输入代码。');
        return;
    }
    
    addMessage('user', '⚡ 优化当前代码');
    
    try {
        const response = await fetch('/api/code/optimize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        
        const data = await response.json();
        editor.setValue(data.code.replace(/```python\n?/g, '').replace(/```\n?/g, ''));
        addMessage('bot', `代码已优化，已更新到编辑器中。\n\n${data.code}`);
    } catch (error) {
        addMessage('bot', '代码优化失败，请稍后重试。');
    }
}

async function debugCode() {
    const code = editor.getValue();
    const error = prompt('请输入错误信息（可选）：');
    
    if (!code.trim()) {
        addMessage('bot', '请先在编辑器中输入代码。');
        return;
    }
    
    addMessage('user', `🐛 调试代码${error ? '，错误信息: ' + error : ''}`);
    
    try {
        const response = await fetch('/api/code/debug', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code, error: error || '' })
        });
        
        const data = await response.json();
        editor.setValue(data.code.replace(/```python\n?/g, '').replace(/```\n?/g, ''));
        addMessage('bot', `调试完成，已更新修复后的代码到编辑器中。\n\n${data.code}`);
    } catch (error) {
        addMessage('bot', '代码调试失败，请稍后重试。');
    }
}

async function explainCode() {
    const code = editor.getValue();
    if (!code.trim()) {
        addMessage('bot', '请先在编辑器中输入代码。');
        return;
    }
    
    addMessage('user', '📝 解释当前代码');
    
    try {
        const response = await fetch('/api/code/explain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        
        const data = await response.json();
        addMessage('bot', data.explanation);
    } catch (error) {
        addMessage('bot', '代码解释失败，请稍后重试。');
    }
}

async function generateTest() {
    const code = editor.getValue();
    if (!code.trim()) {
        addMessage('bot', '请先在编辑器中输入代码。');
        return;
    }
    
    addMessage('user', '🧪 为当前代码生成测试');
    
    try {
        const response = await fetch('/api/code/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        
        const data = await response.json();
        addMessage('bot', `测试代码已生成：\n\n${data.test}`);
    } catch (error) {
        addMessage('bot', '测试生成失败，请稍后重试。');
    }
}

async function generateDoc() {
    const code = editor.getValue();
    if (!code.trim()) {
        addMessage('bot', '请先在编辑器中输入代码。');
        return;
    }
    
    addMessage('user', '📚 为当前代码生成文档');
    
    try {
        const response = await fetch('/api/code/document', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        
        const data = await response.json();
        addMessage('bot', data.documentation);
    } catch (error) {
        addMessage('bot', '文档生成失败，请稍后重试。');
    }
}

function runCode() {
    const code = editor.getValue();
    if (!code.trim()) {
        addMessage('bot', '请先在编辑器中输入代码。');
        return;
    }
    
    addMessage('user', '▶ 运行代码');
    addMessage('bot', '💡 注意：代码在服务端运行，此功能需要额外配置执行环境。当前仅支持代码分析和生成。');
}

function saveCode() {
    const code = editor.getValue();
    if (!code.trim()) {
        addMessage('bot', '请先在编辑器中输入代码。');
        return;
    }
    
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'main.py';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    addMessage('bot', '✅ 代码已保存为 main.py');
}