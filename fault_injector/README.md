# fault_injector

实现了 `RoCE 网络 MTU 不一致` 故障注入示例，支持：

- 统一 conf 文件维护远端服务器登录信息（`fault_injector/conf/fault_injector.conf.json`）
- 注入前先写 WAL（`fault_injector/rollback.wal`）
- WAL 字段：`session_id, operation_id, timestamp, target, recovery_action, status`
- 支持 WAL 原子追加、崩溃后扫描未完成项并恢复
- 支持安全保护：禁止未授权目标、生产命名空间及危险命令模式
- 支持 `simulate`（本地模拟）与 `ssh`（远端真实执行）模式

## 命令

```bash
python -m fault_injector --config fault_injector/conf/fault_injector.conf.json --session-id demo inject-roce-mtu-mismatch
python -m fault_injector --config fault_injector/conf/fault_injector.conf.json --session-id demo rollback
python -m fault_injector --config fault_injector/conf/fault_injector.conf.json --session-id demo --resume rollback
```

把配置中的 `mode` 改为 `ssh` 后即可远端执行。建议先在 `simulate` 模式验证。
