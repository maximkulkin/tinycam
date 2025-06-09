local overseer = require('overseer')

overseer.register_template({
  name = 'Run Tinycam',
  builder = function(params)
    return {
      cmd = { "python3", "-m", "tinycam.main" },
    }
  end,
  tags = { 'RUN' },
})

vim.schedule(function()
  local dap = require('dap')
  dap.configurations.python = {
    {
      type = 'python',
      request = 'launch',
      name = 'Debug Tinycam',
      program = 'tinycam/main.py',
      cwd = vim.fn.getcwd(),
      env = {
        PYTHONPATH = vim.fn.getcwd(),
      },
    },
  }
end)
