#ifndef HAVOK_SCENE_APP_RAGDOLL_PREVIEW_WINDOW_H
#define HAVOK_SCENE_APP_RAGDOLL_PREVIEW_WINDOW_H

#include <QMainWindow>

#include "ragdoll_preview_data.h"

class QLabel;
class QTabWidget;
class QTreeWidget;
class RagdollPreviewViewport;

class RagdollPreviewWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit RagdollPreviewWindow(QWidget* parent = 0);

    void set_preview_data(const RagdollPreviewData& preview_data);
    void clear_preview_data();
    SceneEntityId entity_id() const;

private slots:
    void bone_tree_selection_changed();
    void skeleton_tab_changed(int index);
    void viewport_bone_selected(int bone_index);

private:
    QTreeWidget* active_bone_tree() const;
    const std::vector<RagdollPreviewBone>& active_bones() const;
    void select_bone(int bone_index, bool from_viewport);
    void sync_tree_selection_to_bone(int bone_index);
    void refresh_details();
    void rebuild_bone_trees();
    void refresh_summary();

    RagdollPreviewData m_preview_data;
    RagdollPreviewViewport* m_viewport;
    QTabWidget* m_skeleton_tabs;
    QTreeWidget* m_animation_bone_tree;
    QTreeWidget* m_ragdoll_bone_tree;
    QLabel* m_summary_label;
    QLabel* m_details_label;
    int m_selected_bone_index;
    RagdollPreviewSkeletonKind m_active_skeleton_kind;
};

#endif