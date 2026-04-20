package com.claudeflow.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * 任务实体
 */
@Data
@Entity
@Table(name = "cf01_task")
public class TaskEntity {

    @Id
    @Column(length = 36)
    private String id;

    @Column(length = 100, nullable = false)
    private String name;

    @Column(length = 50, nullable = false)
    private String domain;

    @Column(length = 20, nullable = false)
    private String status;

    @Column(length = 50)
    private String phase;

    @Column
    private Integer progress;

    @Column(length = 100)
    private String sessionId;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(length = 10)
    private String priority;

    @Column
    private LocalDateTime gmtCreate;

    @Column
    private LocalDateTime gmtModified;

    @PrePersist
    public void prePersist() {
        this.gmtCreate = LocalDateTime.now();
        this.gmtModified = LocalDateTime.now();
        if (this.progress == null) {
            this.progress = 0;
        }
        if (this.priority == null) {
            this.priority = "中";
        }
    }

    @PreUpdate
    public void preUpdate() {
        this.gmtModified = LocalDateTime.now();
    }
}