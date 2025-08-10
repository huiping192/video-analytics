# Video Analytics CLI 简化重构计划

## 📊 现状分析

### 当前问题
- **命令过多**: 22个主命令 + 7个子命令 = **29个命令**
- **参数复杂**: 单个命令最多11个参数，用户无法记忆
- **功能重复**: 批量命令泛滥，并行vs串行混乱
- **用户体验差**: 学习成本高，使用复杂

### 当前命令列表

**基础功能 (3个)**
- `info` - 显示视频信息 (9个参数)
- `validate` - 验证文件 (1个参数) ❌ 冗余
- `check` - 检查依赖 (0个参数) ✅ 保留

**单个分析 (3个)** ❌ 全部删除，合并为analyze
- `bitrate` - 视频码率分析 (6个参数)
- `audio` - 音频分析 (6个参数)  
- `fps` - 帧率分析 (6个参数)

**批量分析 (3个)** ❌ 全部删除，用多文件参数替代
- `batch_bitrate` - 批量视频分析 (3个参数)
- `batch_audio` - 批量音频分析 (3个参数)
- `batch_fps` - 批量FPS分析 (3个参数)

**图表生成 (2个)** 
- `chart` - 生成图表 (10个参数) ✅ 保留但简化
- `batch_chart` - 批量图表 (4个参数) ❌ 删除

**并行分析 (3个)** ❌ 全部删除，并行成为默认行为
- `parallel` - 并行分析 (11个参数)
- `batch_parallel` - 批量并行 (8个参数)
- `performance` - 性能测试 (4个参数)

**工具功能 (1个)**
- `download` - 下载视频 (4个参数) ❌ 删除，集成到其他命令

**配置管理 (3个子命令)** ❌ 过度工程化
- `config show/set/reset`

**缓存管理 (4个子命令)** ❌ 合并为一个命令
- `cache list/clear/info/remove`

---

## 🎯 简化方案

### 最终命令结构 (4个主命令)

```bash
# 1. 文件信息
video-analytics info <file> [file2] [file3]...

# 2. 智能分析 (默认并行，所有类型)
video-analytics analyze <file> [file2] [file3]...

# 3. 图表生成
video-analytics chart <file> [file2] [file3]...

# 4. 缓存管理
video-analytics cache <operation>
```

### 核心参数 (仅保留3个)

**全局参数:**
- `--type video,audio,fps` - 选择分析类型 (默认: all)
- `--output ./path` - 输出目录 (默认: ./output)
- `--verbose` - 详细输出 (默认: false)

### 命令详细设计

#### 1. info 命令
```bash
# 替代: info + validate + download功能
video-analytics info video.mp4                    # 单文件
video-analytics info video1.mp4 video2.mp4        # 多文件
video-analytics info https://example.com/video.m3u8  # URL自动下载
```

#### 2. analyze 命令
```bash
# 替代: bitrate + audio + fps + parallel + batch_* 系列
video-analytics analyze video.mp4                 # 全分析(video+audio+fps，并行)
video-analytics analyze video.mp4 --type video    # 只分析视频码率
video-analytics analyze video.mp4 --type video,audio  # 视频+音频
video-analytics analyze *.mp4 --output ./results  # 批量分析
```

#### 3. chart 命令
```bash
# 替代: chart + batch_chart
video-analytics chart video.mp4                   # 生成图表
video-analytics chart *.mp4 --output ./charts     # 批量图表
video-analytics chart video.mp4 --type summary    # 摘要图表
```

#### 4. cache 命令
```bash
# 替代: cache list/clear/info/remove
video-analytics cache --list                      # 列出缓存
video-analytics cache --clear                     # 清理缓存
video-analytics cache --info                      # 缓存信息
video-analytics cache --remove <url>              # 删除指定缓存
```

---

## 🚀 技术实现要点

### 默认行为优化
- **并行处理**: 默认启用，自动检测CPU核心数
- **智能间隔**: 根据文件大小自动优化采样间隔
- **批量处理**: 自动识别多文件参数
- **格式检测**: 自动处理本地文件、HTTP URL、HLS流

### 移除的复杂参数
```bash
# ❌ 删除这些复杂参数
--parallel                    # 默认行为
--max-workers 3               # 自动检测
--enable-video/audio/fps      # 默认全启用
--video-interval 30           # 智能优化
--audio-interval 15           # 智能优化
--fps-interval 10             # 智能优化
--mode fast/detailed          # 根据文件大小自动选择
--force-download              # 智能缓存管理
--workers 10                  # 自动优化
--enhanced                    # 默认行为
--info-level detailed         # 智能选择
--config high_res             # 默认最优
```

### 保留的简单参数
```bash
# ✅ 仅保留必要参数
--type video,audio,fps        # 用户选择分析类型
--output ./path               # 输出位置
--verbose                     # 调试信息
```

---

## 📋 实施计划

### Phase 1: 命令合并
1. 创建新的 `analyze` 命令，整合 `bitrate/audio/fps/parallel` 功能
2. 修改 `info` 命令支持多文件和URL
3. 修改 `chart` 命令支持多文件
4. 创建简化的 `cache` 命令

### Phase 2: 参数简化
1. 移除所有 `--parallel` 相关参数，默认并行
2. 移除复杂的间隔和配置参数，使用智能默认值
3. 移除批量命令的专用参数
4. 统一输出和格式参数

### Phase 3: 清理删除
1. 删除所有 `batch_*` 命令
2. 删除 `parallel/performance` 命令
3. 删除 `validate` 命令
4. 删除 `config` 和 `cache` 子命令组
5. 删除 `download` 命令

### Phase 4: 测试验证
1. 确保向后兼容的关键功能
2. 验证多文件处理逻辑
3. 验证默认并行性能
4. 更新文档和help信息

---

## 📈 预期效果

### 用户体验提升
- **学习成本**: 从29个命令降至4个命令 (-86%)
- **参数复杂度**: 从平均6个参数降至3个参数 (-50%)
- **使用频率**: 90%的用例只需要 `analyze` 命令

### 性能优化
- **默认并行**: 自动获得最佳性能
- **智能优化**: 无需手动调参
- **批量处理**: 自动识别，无需专门命令

### 维护简化
- **代码量**: 预计减少40%的命令处理代码
- **测试复杂度**: 大幅降低
- **文档维护**: 简化90%

---

## ⚠️ 风险评估

### 向后兼容性
- **高风险**: 删除大量现有命令
- **缓解方案**: 提供迁移指南，保留alias支持

### 功能损失
- **低风险**: 所有核心功能保留，仅简化接口
- **用户适应**: 需要更新使用习惯

---

## ✅ 验收标准

1. **4个主命令**涵盖所有原有功能
2. **3个核心参数**满足90%使用场景
3. **零配置使用**，开箱即用
4. **性能不降低**，默认并行处理
5. **向后兼容**关键工作流

---

**总结**: 从29个命令简化到4个命令，从复杂参数简化到智能默认值，大幅提升用户体验的同时保持所有核心功能。