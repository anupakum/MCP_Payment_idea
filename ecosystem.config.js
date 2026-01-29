// PM2 Ecosystem Configuration
// This file ensures services auto-restart on EC2 reboot with proper environment

module.exports = {
  apps: [
    {
      name: 'mcp-server',
      script: '.venv/bin/python',
      args: '-m mcp.http_server',
      cwd: process.env.APP_DIR || '/home/ec2-user/ptr_ag_bnk_pmts_dispute_resol',
      env: {
        UVLOOP_DISABLE: '1',
        PYTHONASYNCIODEBUG: '1',
        USE_MCP_HTTP: 'true'
      },
      autorestart: true,
      watch: false,
      max_restarts: 10,
      restart_delay: 5000,
      exp_backoff_restart_delay: 100
    },
    {
      name: 'backend',
      script: '.venv/bin/python',
      args: '-m mcp.main',
      cwd: process.env.APP_DIR || '/home/ec2-user/ptr_ag_bnk_pmts_dispute_resol',
      env: {
        UVLOOP_DISABLE: '1',
        PYTHONASYNCIODEBUG: '1',
        USE_MCP_HTTP: 'true'
      },
      autorestart: true,
      watch: false,
      max_restarts: 10,
      restart_delay: 5000,
      exp_backoff_restart_delay: 100
    },
    {
      name: 'frontend',
      script: 'npm',
      args: 'run dev',
      cwd: (process.env.APP_DIR || '/home/ec2-user/ptr_ag_bnk_pmts_dispute_resol') + '/web',
      autorestart: true,
      watch: false,
      max_restarts: 10,
      restart_delay: 5000,
      exp_backoff_restart_delay: 100
    }
  ]
};
