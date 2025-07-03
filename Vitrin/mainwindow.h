#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QTimer>
#include "simulator.h"

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void on_loadButton_clicked();
    void on_stepButton_clicked();
    void on_runButton_clicked();
    void on_pauseButton_clicked();
    void updateUI();

private:
    Ui::MainWindow *ui;
    Simulator sim;
    QTimer runTimer;
};

#endif // MAINWINDOW_H
