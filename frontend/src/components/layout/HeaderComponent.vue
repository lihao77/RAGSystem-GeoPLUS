<template>
  <div class="header-container">
    <div class="logo-container">
      <img src="../../assets/logo.svg" alt="Logo" class="logo" v-if="false" />
      <h1 class="title">知识图谱可视化系统</h1>
    </div>
    <div class="user-info">
      <el-dropdown>
        <span class="el-dropdown-link">
          <el-icon><Setting /></el-icon>
          系统设置
          <el-icon class="el-icon--right"><arrow-down /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="navigateTo('/settings')">参数配置</el-dropdown-item>
            <el-dropdown-item @click="navigateTo('/import')">数据导入</el-dropdown-item>
            <el-dropdown-item divided>帮助文档</el-dropdown-item>
            <el-dropdown-item>关于系统</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';

const router = useRouter();

const navigateTo = (path) => {
  router.push(path);
};
</script>

<style scoped>
.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 100%;
}

.logo-container {
  display: flex;
  align-items: center;
}

.logo {
  height: 40px;
  margin-right: 10px;
}

.title {
  font-size: 20px;
  font-weight: bold;
  color: white;
  margin: 0;
}

.user-info {
  display: flex;
  align-items: center;
}

.el-dropdown-link {
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
}
</style>