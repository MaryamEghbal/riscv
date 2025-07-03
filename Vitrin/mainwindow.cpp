#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QFileDialog>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent),
    ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    connect(&runTimer, &QTimer::timeout, this, &MainWindow::on_stepButton_clicked);

    updateUI();
}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::updateUI()
{
    const auto &regs = sim.getRegisters();
    QString regText;

    for (int i = 0; i < static_cast<int>(regs.size()); ++i) {
        regText += QString("x%1: 0x%2\n")
                       .arg(i, 2, 10, QChar('0'))
                       .arg(regs[i], 8, 16, QChar('0'));
    }

    ui->registersText->setPlainText(regText);
    ui->pcLabel->setText(QString("PC: 0x%1").arg(sim.getPC(), 8, 16, QChar('0')));


    QString memText;
    const auto &memory = sim.getMemory();

    const uint32_t base = 0x1000;
    const uint32_t size = 0x0100;

    for (uint32_t addr = base; addr < base + size; addr += 16) {
        memText += QString("0x%1: ").arg(addr, 8, 16, QChar('0'));
        for (int i = 0; i < 16; ++i) {
            memText += QString("%1 ").arg(memory[addr + i], 2, 16, QChar('0')).toUpper();
        }
        memText += "\n";
    }

    ui->memoryText->setPlainText(memText);
}

void MainWindow::on_loadButton_clicked()
{
    QString fileName = QFileDialog::getOpenFileName(this, "Load Program", "", "Binary Files (*.bin)");
    if (!fileName.isEmpty()) {
        sim.reset();
        if (sim.loadProgram(fileName)) {
            updateUI();
        }
    }
}

void MainWindow::on_stepButton_clicked()
{
    sim.step();
    updateUI();
}

void MainWindow::on_runButton_clicked()
{
    runTimer.start(200);
}

void MainWindow::on_pauseButton_clicked()
{
    runTimer.stop();
}
