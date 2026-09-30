/**
 * API 模块统一导出
 *
 * 所有模块 API 已按领域拆分到 api/modules/ 目录下。
 * 此文件向后兼容，保留所有旧导入路径。
 *
 * 新代码建议按需导入：
 *   import { getDevices } from '@/api/modules/energy'
 *   import { getPatients } from '@/api/modules/medical'
 */

export * from './modules/development'
export * from './modules/energy'
export * from './modules/environment'
export * from './modules/medical'
export * from './modules/finance'
export * from './modules/traffic'
// 教育模块和创意设计模块已移除
export * from './modules/forum'
export * from './modules/public'
