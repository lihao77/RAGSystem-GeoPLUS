<template>
    <div class="graph-container">
        <div id="forceGraphContainer" ref="forceGraphContainer" class="force-graph"></div>

        <!-- 控制面板 -->
        <div class="graph-controls">
            <button @click="showCompleteGraph" class="control-btn">
                <span class="btn-icon">🔍</span> 显示全图
            </button>
            <button @click="reloadFullGraph" class="control-btn">
                <span class="btn-icon">🔄</span> 刷新图谱
            </button>
        </div>

        <!-- 图例说明 -->
        <div class="graph-legend">
            <h4>图例</h4>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #ff5722;"></span>
                <span>地点</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #4caf50;"></span>
                <span>设施</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #2196f3;"></span>
                <span>状态</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #ffc107;"></span>
                <span>事件</span>
            </div>
        </div>

        <!-- 实体信息面板 -->
        <div v-if="selectedEntity" class="entity-info">
            <h3>{{ selectedEntity.name || selectedEntity.id }}</h3>
            <div class="entity-type">{{ selectedEntity.type }}</div>
            <div v-if="selectedEntity.time" class="entity-time">{{ formatTime(selectedEntity.time) }}</div>
            <div v-if="selectedEntity.geo" class="entity-geo">{{ selectedEntity.latitude }}, {{ selectedEntity.longitude }}</div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, shallowRef, markRaw } from 'vue';
import ForceGraph3D from '3d-force-graph';
import * as THREE from 'three';
import SpriteText from 'three-spritetext';
import { entityService } from '../../api';

// 节流函数 - 限制高频事件触发
const throttle = (fn, delay) => {
    let lastCall = 0;
    return function (...args) {
        const now = Date.now();
        if (now - lastCall >= delay) {
            lastCall = now;
            return fn.apply(this, args);
        }
    };
};

// 响应式状态
const forceGraphContainer = shallowRef(null);
const forceGraph = shallowRef(null);
const graphData = ref({ nodes: [], links: [] });
const selectedEntity = ref(null);
// 接收父组件传递的属性
const props = defineProps({
    // 当前选中的实体
    entityId: {
        type: String,
        default: null
    },
    viewMode: {
        type: String,
        default: 'split' // 'map', 'graph', 'split'
    }
});

// 向父组件发送事件
const emit = defineEmits(['select-entity']);

// 初始化力导向图
onMounted(() => {
    initForceGraph();
    loadGraphData();

    // 添加窗口大小变化的监听器
    window.addEventListener('resize', handleResize);
});

// 在组件销毁时清理资源
onUnmounted(() => {
    if (forceGraph.value) {
        forceGraph.value._destructor();
    }

    // 移除窗口大小变化的监听器
    window.removeEventListener('resize', handleResize);
});

// 处理窗口大小变化
const handleResize = () => {
    if (forceGraphContainer.value && forceGraph.value) {
        // 更新画布尺寸
        updateGraphDimensions();
        // 重新渲染图形
        forceGraph.value.refresh();
    }
};

// 更新图形尺寸
const updateGraphDimensions = () => {
    if (forceGraphContainer.value && forceGraph.value) {
        // 获取容器的当前尺寸
        const width = forceGraphContainer.value.clientWidth;
        const height = forceGraphContainer.value.clientHeight;

        // 设置图形尺寸
        forceGraph.value.width(width);
        forceGraph.value.height(height);
    }
};

// 加载图谱数据
const loadGraphData = async () => {
    try {
        const data = await entityService.getKnowledgeGraph();

        // 转换数据为力导向图所需格式
        const nodes = data.entities.map(entity => ({
            id: entity.id,
            name: entity.name || entity.value || entity.type || entity.id,
            type: entity.type,
            longitude: entity.longitude,
            latitude: entity.latitude,
            time: entity.time,
            geo: entity.geo,
            entityIds: entity.entityIds,
            // 为3D图添加属性
            val: entity.type === '地点' ? 20 :
                entity.type === '设施' ? 15 :
                    entity.type === 'State' ? 10 :
                        entity.type === '事件' ? 12 : 8,
            highlight: false
        }));
        const links = data.relationships
            .filter(rel => {
                // 验证source和target是否存在且有效
                const sourceExists = nodes.some(node => node.id === rel.source);
                const targetExists = nodes.some(node => node.id === rel.target);
                return sourceExists && targetExists && rel.source && rel.target;
            })
            .map(rel => ({
                source: rel.source,
                target: rel.target,
                type: rel.name || rel.type,
                entities: rel.entities,
                highlight: false
            }));

        graphData.value = { nodes, links };
        // 更新力导向图数据
        if (forceGraph.value) {
            forceGraph.value.graphData({
                nodes,
                links
            });

            // 更新画布尺寸
            updateGraphDimensions();

            // 如果有选中的实体，高亮显示
            if (props.entityId) {
                highlightEntityAndRelated(props.entityId);
            } else {
                // 初始加载时，确保图形能完整显示
                forceGraph.value.zoomToFit(400, 1000);
            }
        }
    } catch (err) {
        console.error('获取数据错误:', err);
    }
};

// 处理节点点击事件
const handleNodeClick = (node) => {
    selectedEntity.value = node;
    emit('select-entity', node);
};

// 高亮显示实体及其相关节点
const highlightEntityAndRelated = async (entityId) => {
    if (!graphData.value || !graphData.value.nodes.length) return;

    // 重置所有节点和连接的高亮状态
    graphData.value.nodes.forEach(node => node.highlight = false);
    graphData.value.links.forEach(link => link.highlight = false);

    // 找到目标实体节点
    const targetNode = graphData.value.nodes.find(node => node.id === entityId);
    if (!targetNode) return;

    // 高亮目标节点
    targetNode.highlight = true;

    // 找出与目标节点直接相连的所有连接和节点
    const relatedLinks = graphData.value.links.filter(
        link => link.source === entityId || link.target === entityId ||
            (typeof link.source === 'object' && link.source.id === entityId) ||
            (typeof link.target === 'object' && link.target.id === entityId)
    );

    // 高亮相关连接
    relatedLinks.forEach(link => link.highlight = true);

    // 高亮相关节点
    const relatedNodeIds = new Set();
    relatedLinks.forEach(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        relatedNodeIds.add(sourceId);
        relatedNodeIds.add(targetId);
    });

    // 创建一个新的节点数组，只包含相关节点
    const visibleNodes = graphData.value.nodes.filter(node =>
        node.id === entityId || relatedNodeIds.has(node.id)
    );

    // 创建一个新的连接数组，只包含相关连接
    const visibleLinks = graphData.value.links.filter(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        return relatedNodeIds.has(sourceId) && relatedNodeIds.has(targetId);
    });

    // 如果是地点或设施，获取其状态链和相关事件
    if (targetNode.type === '地点' || targetNode.type === '设施') {
        try {
            // 获取状态链
            const statesData = await entityService.getEntityStates(entityId);

            // 高亮状态链中的所有状态节点
            statesData.states.forEach(state => {
                const stateNode = graphData.value.nodes.find(node => node.id === state.id);
                if (stateNode) {
                    stateNode.highlight = true;
                    relatedNodeIds.add(state.id);
                    // 添加到可见节点
                    if (!visibleNodes.some(node => node.id === state.id)) {
                        const node = graphData.value.nodes.find(n => n.id === state.id);
                        if (node) visibleNodes.push(node);
                    }
                }
            });

            // 获取相关事件
            const eventsData = await entityService.getEntityEvents(entityId);
            // 高亮相关事件及其状态
            eventsData.forEach(event => {
                const eventNode = graphData.value.nodes.find(node => node.id === event.id);
                if (eventNode) {
                    eventNode.highlight = true;
                    relatedNodeIds.add(event.id);
                    // 添加到可见节点
                    if (!visibleNodes.some(node => node.id === event.id)) {
                        visibleNodes.push(eventNode);
                    }
                }

                // 高亮事件的状态
                if (event.states) {
                    event.states.forEach(stateId => {
                        const stateNode = graphData.value.nodes.find(node => node.id === stateId);
                        if (stateNode) {
                            stateNode.highlight = true;
                            relatedNodeIds.add(stateId);
                            // 添加到可见节点
                            if (!visibleNodes.some(node => node.id === stateId)) {
                                visibleNodes.push(stateNode);
                            }
                        }
                    });
                }
            });
        } catch (err) {
            console.error('获取相关数据错误:', err);
        }
    }

    // 更新可见连接，确保包含所有相关节点之间的连接
    graphData.value.links.forEach(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        if (relatedNodeIds.has(sourceId) && relatedNodeIds.has(targetId)) {
            if (link.type === 'nextState' || link.type === 'contain') {
                if (link.entities.includes(entityId)) {
                    link.highlight = true;
                    if (!visibleLinks.some(l =>
                        (l.source === link.source && l.target === link.target) ||
                        (l.source === link.target && l.target === link.source)
                    )) {
                        visibleLinks.push(link);
                    }
                }
            } else {
                link.highlight = true;
                if (!visibleLinks.some(l =>
                    (l.source === link.source && l.target === link.target) ||
                    (l.source === link.target && l.target === link.source)
                )) {
                    visibleLinks.push(link);
                }
            }
        }
    });

    // 更新力导向图数据，只显示相关节点和连接
    if (forceGraph.value) {
        forceGraph.value.graphData({
            nodes: visibleNodes,
            links: visibleLinks
        });
    }

    // 聚焦到目标节点
    if (forceGraph.value && targetNode) {

        const graphNode = forceGraph.value.graphData().nodes.find(n => n.id === targetNode.id);
        if (graphNode) {
            // 使用zoomToFit并指定只包裹目标节点
            forceGraph.value.zoomToFit(1000, 3000, node => node.id === targetNode.id);
        } else {
            // 如果找不到节点或节点没有坐标，则使用zoomToFit
            forceGraph.value.zoomToFit(1000, 3000);
        }
    }
    // 更新选中的实体
    selectedEntity.value = targetNode;
};

// 重置图谱高亮并显示完整图谱
const resetGraphHighlight = () => {
    if (!graphData.value) return;

    graphData.value.nodes.forEach(node => node.highlight = false);
    graphData.value.links.forEach(link => link.highlight = false);

    // 恢复显示所有节点和连接
    if (forceGraph.value) {
        forceGraph.value.graphData({
            nodes: graphData.value.nodes,
            links: graphData.value.links
        });
        // 更新画布尺寸
        updateGraphDimensions();
    }
};

// 显示完整图谱
const showCompleteGraph = () => {
    selectedEntity.value = null;

    // 重置视图
    if (forceGraph.value) {
        forceGraph.value.graphData({
            nodes: graphData.value.nodes,
            links: graphData.value.links
        });
        // 更新画布尺寸
        updateGraphDimensions();
        // 增加动画持续时间并减小缩放偏移量，确保能看到完整图谱
        forceGraph.value.zoomToFit(400, 3000);
    }
};

// 更新力导向图
const updateForceGraph = () => {
    if (!forceGraph.value) return;

    // 更新画布尺寸
    updateGraphDimensions();
    forceGraph.value.refresh();
};

// 重新加载完整图谱
const reloadFullGraph = () => {
    if (!forceGraph.value || !graphData.value) return;

    forceGraph.value.graphData({
        nodes: graphData.value.nodes,
        links: graphData.value.links
    });
    // 更新画布尺寸
    updateGraphDimensions();
    setTimeout(() => {
        forceGraph.value.zoomToFit(1000, 100);
    }, 500);
};

// 格式化时间显示
const formatTime = (timeString) => {
    if (!timeString) return '未知时间';

    // 处理时间范围格式 (2023-10-01至2023-10-10)
    if (timeString.includes('至')) {
        const [start, end] = timeString.split('至');
        return `${formatDate(start)} 至 ${formatDate(end)}`;
    }

    return formatDate(timeString);
};

// 格式化日期
const formatDate = (dateString) => {
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString; // 如果无法解析，返回原始字符串

        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (e) {
        return dateString;
    }
};

// 监听entityId变化，更新选中的实体和相关节点
watch(() => props.entityId, (newId) => {
    if (newId) {
        highlightEntityAndRelated(newId);
    } else {
        // 当取消选择实体时，显示完整图谱
        showCompleteGraph();
        selectedEntity.value = null;
    }
}, { immediate: true });


// 监听viewMode变化，
watch(() => props.viewMode, () => {
    // 刷新图形以适应新视图模式
    setTimeout(() => {
        updateForceGraph();
    }, 0);
    console.log('viewMode changed:', props.viewMode);
}, { immediate: true });
// 初始化3D力导向图
const initForceGraph = () => {
    if (!forceGraphContainer.value) return;

    // 更新图形尺寸
    updateGraphDimensions();

    forceGraph.value = ForceGraph3D()(forceGraphContainer.value)
        .backgroundColor('rgba(0,10,30,0.9)')
        .nodeLabel(node => `${node.name || node.id}${node.type ? ` (${node.type})` : ''}`)
        .nodeAutoColorBy('type')
        .cooldownTicks(20) // 减少冷却时间，加快稳定速度
        .d3AlphaDecay(0.1) // 加快alpha衰减
        .d3VelocityDecay(0.2) // 加快速度衰减
        .nodeThreeObject(node => {
            // 统一使用球形几何体，根据节点类型调整大小
            const radius = node.type === 'State' ? 6 :
                node.type === '事件' ? 8 :
                    node.type === '地点' ? 7 :
                        node.type === '设施' ? 7 :
                            5;
            const geometry = markRaw(new THREE.SphereGeometry(radius));

            // 设置材质和颜色，使用更鲜艳的颜色
            const color = node.type === '地点' ? '#ff5722' :
                node.type === '设施' ? '#4caf50' :
                    node.type === 'State' ? '#2196f3' :
                        node.type === '事件' ? '#ffc107' : '#9e9e9e';

            // 创建发光材质效果
            const material = markRaw(new THREE.MeshPhongMaterial({
                color,
                transparent: true,
                opacity: node.highlight ? 1 : 0.75,
                shininess: 80,
                specular: new THREE.Color(node.highlight ? 0xffffff : 0x111111)
            }));

            const mesh = markRaw(new THREE.Mesh(geometry, material));

            // 添加文本标签，优化显示效果
            const sprite = markRaw(new SpriteText(node.name || node.id));
            sprite.color = node.highlight ? '#ffffff' : '#dddddd';
            sprite.backgroundColor = node.highlight ? color : 'rgba(0,0,0,0.4)';
            sprite.padding = 3;
            sprite.borderRadius = 4;
            sprite.textHeight = node.highlight ? 5 : 4;
            // 统一调整标签位置到球体上方
            sprite.position.y = 16;

            // 创建组合对象
            const group = markRaw(new THREE.Group());
            group.add(mesh);
            group.add(sprite);

            return group;
        })
        .linkDirectionalArrowLength(5)
        .linkDirectionalArrowRelPos(1)
        .linkDirectionalArrowColor(link => link.highlight ? '#ffffff' : '#aaaaaa')
        .linkWidth(link => link.highlight ? 3 : 1.2)
        .linkColor(link => {
            // 根据连接类型设置不同颜色
            if (link.highlight) return '#ffff00';
            if (link.type && link.type.includes('发生')) return '#ff9800';
            if (link.type && link.type.includes('位于')) return '#03a9f4';
            if (link.type && link.type.includes('影响')) return '#e91e63';
            return 'rgba(200,200,200,0.5)';
        })
        .linkLabel(link => link.type)
        .linkCurvature(0.1) // 添加曲率使连线更美观
        .linkDirectionalParticles(link => link.highlight ? 3 : 0) // 高亮连接添加粒子效果，减少粒子数量以降低渲染负担
        .linkDirectionalParticleWidth(3) // 减小粒子宽度
        .linkDirectionalParticleSpeed(0.008) // 降低粒子速度
        .onNodeClick(handleNodeClick)
        .onNodeHover(node => {
            if (forceGraphContainer.value) {
                forceGraphContainer.value.style.cursor = node ? 'pointer' : 'default';
            }
        })
        // .onLinkHover(throttle((link) => {
        //     // 连接悬停效果 - 使用节流函数减少高频触发
        //     if (!forceGraph.value) return;

        //     // 当前没有悬停在任何链接上
        //     if (!link) {
        //         // 检查是否有需要恢复的高亮连接
        //         let needsRefresh = false;
        //         graphData.value.links.forEach(l => {
        //             if (l.highlight && !l.__permanently_highlighted) {
        //                 l.highlight = false;
        //                 needsRefresh = true;
        //             }
        //         });

        //         // 只有在确实有变化时才刷新
        //         if (needsRefresh) {
        //             forceGraph.value.refresh();
        //         }
        //         return;
        //     }

        //     // 如果链接已经是高亮状态，不需要重复操作
        //     if (link.highlight) return;

        //     // 设置高亮并刷新
        //     link.highlight = true;
        //     forceGraph.value.refresh();
        // }, 100)) // 100ms的节流延迟，可根据实际性能调整

        // 添加缩放控制
        .enableNodeDrag(true)
        .enableNavigationControls(true)
        .showNavInfo(true)

};


</script>

<style scoped>
.graph-container {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
}

.force-graph {
    width: 100%;
    height: 100%;
}

/* 控制面板样式 */
.graph-controls {
    position: absolute;
    top: 20px;
    right: 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    z-index: 10;
}

.control-btn {
    background-color: rgba(10, 20, 40, 0.85);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
    transition: all 0.2s ease;
    backdrop-filter: blur(5px);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}

.control-btn:hover {
    background-color: rgba(30, 40, 60, 0.9);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.btn-icon {
    margin-right: 6px;
    font-size: 16px;
}

/* 图例样式 */
.graph-legend {
    position: absolute;
    top: 20px;
    left: 20px;
    background-color: rgba(10, 20, 40, 0.85);
    color: white;
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(5px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    z-index: 10;
}

.graph-legend h4 {
    margin-top: 0;
    margin-bottom: 10px;
    font-size: 16px;
    font-weight: 500;
    color: #ffffff;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    padding-bottom: 6px;
}

.legend-item {
    display: flex;
    align-items: center;
    margin-bottom: 6px;
}

.legend-color {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    margin-right: 8px;
    box-shadow: 0 0 4px rgba(0, 0, 0, 0.3);
}

.entity-info {
    position: absolute;
    bottom: 20px;
    left: 20px;
    background-color: rgba(10, 20, 40, 0.85);
    color: white;
    border-radius: 12px;
    padding: 16px;
    max-width: 320px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(5px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all 0.3s ease;
    transform-origin: bottom left;
    animation: fadeIn 0.5s ease-out;
}

.entity-info h3 {
    margin-top: 0;
    margin-bottom: 10px;
    font-size: 18px;
    font-weight: 600;
    color: #ffffff;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    padding-bottom: 8px;
}

.entity-type {
    font-size: 14px;
    color: #4caf50;
    margin-bottom: 8px;
    font-weight: 500;
    display: inline-block;
    padding: 3px 8px;
    background-color: rgba(76, 175, 80, 0.2);
    border-radius: 4px;
}

.entity-time,
.entity-geo {
    font-size: 13px;
    color: #e0e0e0;
    margin-top: 8px;
    display: flex;
    align-items: center;
}

.entity-time:before {
    content: '🕒';
    margin-right: 6px;
}

.entity-geo:before {
    content: '📍';
    margin-right: 6px;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.graph-container {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
}

.force-graph {
    width: 100%;
    height: 100%;
}

/* 控制面板样式 */
.graph-controls {
    position: absolute;
    top: 20px;
    right: 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    z-index: 10;
}

.control-btn {
    background-color: rgba(10, 20, 40, 0.85);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
    transition: all 0.2s ease;
    backdrop-filter: blur(5px);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}

.control-btn:hover {
    background-color: rgba(30, 40, 60, 0.9);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.btn-icon {
    margin-right: 6px;
    font-size: 16px;
}

/* 图例样式 */
.graph-legend {
    position: absolute;
    top: 20px;
    left: 20px;
    background-color: rgba(10, 20, 40, 0.85);
    color: white;
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(5px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    z-index: 10;
}

.graph-legend h4 {
    margin-top: 0;
    margin-bottom: 10px;
    font-size: 16px;
    font-weight: 500;
    color: #ffffff;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    padding-bottom: 6px;
}

.legend-item {
    display: flex;
    align-items: center;
    margin-bottom: 6px;
}

.legend-color {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    margin-right: 8px;
    box-shadow: 0 0 4px rgba(0, 0, 0, 0.3);
}

.entity-info {
    position: absolute;
    bottom: 20px;
    left: 20px;
    background-color: rgba(10, 20, 40, 0.85);
    color: white;
    border-radius: 12px;
    padding: 16px;
    max-width: 320px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(5px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all 0.3s ease;
    transform-origin: bottom left;
    animation: fadeIn 0.5s ease-out;
}

.entity-info h3 {
    margin-top: 0;
    margin-bottom: 10px;
    font-size: 18px;
    font-weight: 600;
    color: #ffffff;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    padding-bottom: 8px;
}

.entity-type {
    font-size: 14px;
    color: #4caf50;
    margin-bottom: 8px;
    font-weight: 500;
    display: inline-block;
    padding: 3px 8px;
    background-color: rgba(76, 175, 80, 0.2);
    border-radius: 4px;
}

.entity-time,
.entity-geo {
    font-size: 13px;
    color: #e0e0e0;
    margin-top: 8px;
    display: flex;
    align-items: center;
}

.entity-time:before {
    content: '🕒';
    margin-right: 6px;
}

.entity-geo:before {
    content: '📍';
    margin-right: 6px;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>