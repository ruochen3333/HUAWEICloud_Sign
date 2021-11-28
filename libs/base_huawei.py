import asyncio
import json
import os
import random
import string
import time

import requests
from pyppeteer.network_manager import Response

from libs.base import BaseClient

name_map = {
    '项目管理': [['week_new_project', 0], ['week_new_member', 1], ['new_work_project', 2]],
    '代码托管': [['week_new_git', 0], ['open_code_task', 1], ['push_code_task', 2]],
    'CloudIDE': [['open_ide_task', 0]],
    '代码检查': [['week_new_code_check', 0], ['check_code_task', 1]],
    '编译构建': [['week_new_compile_build', 0], ['compile_build_task', 1]],
    '部署': [['week_new_deploy_task', 0], ['deploy_task', 1]],
    '发布': [['upload_task', 0]],
    '流水线': [['week_new_pipeline', 0], ['pipeline_task', 1]],
    '接口测试': [['week_new_api_test_task', 0], ['api_test_task', 1]],
    # '接口测试': [['api_test_task', 0]],
    '测试管理': [['new_test_task', 0], ['run_test_task', 1]],
    'APIG网关': [['new_new_api_task', 0], ['run_api_task', 1], ['debug_api_task', 2]],
    '函数工作流': [['new_fun_task', 0]],
    '使用API Explorer完在线调试': 'api_explorer_task',
    '使用API Explorer在线调试': 'api2_explorer_task',
    '使用Devstar生成代码工程': 'dev_star_task',
    '浏览Codelabs代码示例': 'view_code_task',
    '体验DevStar快速生成代码': 'fast_dev_star',
}

init_name_map = {
    # '项目管理': [['week_new_project', 0]],
    # '代码托管': [['week_new_git', 0]],
    # '代码检查': [['week_new_code_check', 0]],
    # '编译构建': [['week_new_compile_build', 0]],
    # '部署': [['week_new_deploy', 0]],
    # '流水线': [['week_new_pipeline', 0]],
    '使用API  Explorer完在线调试': 'api_explorer_task',
    '使用API Explorer在线调试': 'api_explorer_task',
    # '使用Devstar生成代码工程': 'dev_star_task',
}


class BaseHuaWei(BaseClient):

    def __init__(self):
        super().__init__()
        self.url = 'https://devcloud.huaweicloud.com/bonususer/home/makebonus'
        self.task_page = None
        self.create_done = True
        self.home_url = None
        self.cancel = False
        self.header_url = None
        self.resultsJSON = {}

    async def start(self):
        if self.page.url != self.url:
            await self.page.goto(self.url, {'waitUntil': 'load'})

        id_list = ['experience-missions', 'middleware-missions']
        for _id in id_list:
            try:
                await self.execute(_id, 'ul.devui-nav li.ng-star-inserted', '', True, name_map)
            except Exception as e:
                self.logger.debug(e)

        try:
            await self.regular()
        except Exception as e:
            self.logger.debug(e)

        try:
            await self.init_account()
        except Exception as e:
            self.logger.debug(e)

    async def regular(self):
        await self.execute('regular-missions', '.daily-list li', 'feedback-', False, name_map)

    async def init_account(self):
        # await self.execute('experience-missions', 'ul.devui-nav li.ng-star-inserted', '', True, init_name_map)

        await self.page.goto('https://devcloud.huaweicloud.com/bonususer/home/new', {'waitUntil': 'load'})
        await asyncio.sleep(2)
        await self.execute('new-tasks-box', 'li.hot-task-item', 'new-task', False, init_name_map)

    async def execute(self, element_id, element_list_name, task_node, is_tab=True, task_map=None):
        elements = await self.page.querySelectorAll(f'#{element_id} {element_list_name}')
        for i, element in enumerate(elements):
            if self.cancel:
                break

            if is_tab:
                name = str(await element.Jeval('a', 'el => el.textContent')).strip()
                task_list = task_map.get(name)
                if task_list is None:
                    continue

                for task in task_list:
                    await element.click()
                    await asyncio.sleep(1)
                    task_node = f'#{element_id} #{element_id}-{task[1]}'
                    await self.run_task(task_node, task[0])
            else:
                _task_node = f'#{element_id} #{task_node}{i}'
                task_name = str(await self.page.Jeval(f'{_task_node} h5', 'el => el.textContent')).strip()
                self.resultsJSON[f'{task_name}'] = 'NODONE'
                if not task_map.get(task_name):
                    continue

                await self.run_task(_task_node, task_map.get(task_name))

    async def is_done(self, node, task_fun):
        try:
            is_done = await self.page.querySelector(f"{node} .complate-img")
            if is_done:
                if self.create_done and 'week' in task_fun:
                    return False
                return True
            is_done = await self.page.querySelector(f"{node} img.completed")
            if is_done:
                if self.create_done and 'week' in task_fun:
                    return False
                return True
        except Exception as e:
            self.logger.debug(e)
        return False

    async def run_task(self, task_node, task_fun):
        task_name = await self.page.Jeval(f'{task_node} h5', 'el => el.textContent')

        if await self.is_done(task_node, task_fun):
            self.logger.warning(f'{task_name} -> DONE.')
            self.resultsJSON[f'{task_name}'] = 'DONE'
            return True

        await self.page.click(task_node)
        await asyncio.sleep(2)
        self.logger.warning(f'{task_name}')

        try:
            self.task_page = await self.get_new_page()
            await self.task_page.setUserAgent(self.ua)
        except Exception as e:
            self.logger.error(e)
            raise e

        try:
            func = getattr(self, task_fun)
            # await func()
            await asyncio.wait_for(func(), timeout=100.0)
            self.logger.warning(f'{task_name} -> DONE.')
            self.resultsJSON[f'{task_name}'] = 'DONE'
        except asyncio.TimeoutError as t:
            self.logger.debug(t)
            # await self.send_photo(self.task_page, task_fun)
        except Exception as e:
            self.logger.error(e)
        finally:
            await self.close_page()
            await asyncio.sleep(2)
            return True

    async def get_credit(self):
        await asyncio.sleep(8)
        result = {'码豆': 0, 'uid': ''}

        async def intercept_response(response: Response):
            global uid
            url = response.url
            if 'bonususer/rest/me' in url:
                data = json.loads(await response.text())
                result['uid'] = data.get('id')

        self.page.on('response', intercept_response)

        for i in range(3):
            if self.page.url != self.url:
                await self.page.goto(self.url, {'waitUntil': 'load'})
            else:
                await self.page.reload({'waitUntil': 'load'})

            await asyncio.sleep(5)

            try:
                s = await self.page.Jeval('#homeheader-coins', 'el => el.textContent')
                result['码豆'] = str(s).replace('码豆', '').strip()
                self.resultsJSON['码豆'] = str(s).replace('码豆', '').strip()
                break
            except Exception as e:
                self.logger.debug(e)
        return result

    async def sign_task(self):
        try:
            await asyncio.sleep(5)
            info = await self.page.Jeval(
                '#homeheader-signin span.button-content, #homeheader-signined span.button-content',
                'el => el.textContent')
            sign_txt = str(info).strip()
            self.logger.info(sign_txt)
            if sign_txt.find('已签到') == -1:
                await self.page.click('#homeheader-signin')
                await asyncio.sleep(3)
        except Exception as e:
            self.logger.warning(e)

    async def get_new_page(self):
        await asyncio.sleep(2)
        await self.page.click('.modal.in .modal-footer .devui-btn')
        await asyncio.sleep(5)
        page_list = await self.browser.pages()
        await page_list[-1].setViewport({'width': self.width + 560, 'height': self.height})
        return page_list[-1]

    async def close_page(self):
        page_list = await self.browser.pages()
        if len(page_list) > 1:
            page = page_list[-1]
            if page.url != self.url:
                await page.close()

    # API接口用例测试
    async def api_explorer_task(self):
        await asyncio.sleep(2)
        html = str(await self.task_page.JJeval('.userInfo', '(els) => els.map(el => el.outerHTML)'))
        if html.find('English') != -1:
            items = await self.task_page.querySelectorAll('.userInfo')
            await items[1].hover()
            await asyncio.sleep(2)
            await self.task_page.click('.cdk-overlay-container .dropdown-item')
            await asyncio.sleep(5)

        url = 'https://apiexplorer.developer.huaweicloud.com/apiexplorer/overview'
        # 2021年10月13日11:55:40增加查看华为云官方API
        await self.task_page.goto(url, {'waitUntil': 'load'})
        await asyncio.sleep(10)
        if self.task_page.url == url:
            url = 'https://apiexplorer.developer.huaweicloud.com/apiexplorer/doc?product=DevStar&api=ListPublishedTemplates'
            await self.task_page.goto(url, {'waitUntil': 'load'})
            await asyncio.sleep(3)

        await self.task_page.click('#debug')
        await asyncio.sleep(3)

    # API接口用例测试
    # 正常
    async def api2_explorer_task(self):
        _url = 'https://apiexplorer.developer.huaweicloud.com/apiexplorer/doc?product=DevStar&api=ListPublishedTemplates'
        await self.task_page.goto(_url, {'waitUntil': 'load'})
        await self.api_explorer_task()

    async def dev_star_task(self):
        await asyncio.sleep(2)
        await self.task_page.waitForSelector('#confirm-download-btn', {'visible': True})
        await self.task_page.click('.template-dynamic-paramter-title .devui-btn')
        await asyncio.sleep(2)
        await self.task_page.click('#confirm-upload-btn')
        await asyncio.sleep(3)

    async def view_code_task(self):
        await asyncio.sleep(10)
        codelabsUrl = 'https://codelabs.developer.huaweicloud.com/codelabs'
        await self.task_page.goto(codelabsUrl, {'waitUntil': 'load'})
        await asyncio.sleep(5)
        await self.task_page.click('#code-template-card-title')
        await asyncio.sleep(5)
        # await self.task_page.click('#code-template-cards .card-width:nth-child(2) .code-template-card-title')
        # await asyncio.sleep(2)

    async def open_code_task(self):
        await asyncio.sleep(5)
        codehubUrl = 'https://devcloud.cn-north-4.huaweicloud.com/codehub/home'
        await self.task_page.goto(codehubUrl, {'waitUntil': 'load'})
        await asyncio.sleep(5)
        await self.task_page.click('#repoNamephoenix-sample')
        await asyncio.sleep(5)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#codehub-main-content > app-repo-header > div > div > div.repo-info-right.ng-star-inserted > operate-btn-header > ul > li:nth-child(4) > d-button > button').click(); }''')
        await asyncio.sleep(60)

        # 原作者代码，已失效
        # items = await self.task_page.querySelectorAll('div.devui-table-view tbody tr')
        # if items and len(items):
        #     await self.task_page.evaluate(
        #         '''() =>{ document.querySelector('div.devui-table-view tbody tr:nth-child(1) td:nth-child(8) i.icon-more-operate').click(); }''')
        #     await asyncio.sleep(1)
        #     await self.task_page.evaluate(
        #         '''() =>{ document.querySelector('ul.dropdown-menu li:nth-child(5) .devui-btn').click(); }''')
        #     await asyncio.sleep(20)

    async def open_ide_task(self):
        await asyncio.sleep(5)
        try:
            await self.task_page.click('.region-modal-button-content .region-modal-button-common')
            await asyncio.sleep(1)
        except Exception as e:
            self.logger.debug(e)

        await asyncio.sleep(3)
        await self.task_page.click(
            '.trial-stack-info .trial-stack:nth-child(1) .stack-content .stack-position .devui-btn')
        await asyncio.sleep(10)

    async def push_code_task(self):
        if self.git:
            now_time = time.strftime('%Y-%m-%d %H:%M:%S')
            cmd = [
                'cd /tmp',
                'git config --global user.name "caoyufei" && git config --global user.email "atcaoyufei@gmail.com"',
                f'git clone {self.git}',
                'cd /tmp/crawler',
                f'echo "{now_time}" >> time.txt',
                "git add .",
                "git commit -am 'time'",
                "git push origin master",
            ]
            os.system(' && '.join(cmd))
            os.system('rm -rf /tmp/crawler')
            await asyncio.sleep(1)

    async def week_new_compile_build(self):
        await asyncio.sleep(2)
        await self.task_page.waitForSelector('.devui-layout-main-content', {'visible': True})
        await self.task_page.click('.devui-layout-main-content #create_new_task')
        await asyncio.sleep(5)
        await self.task_page.click('div.step-footer div.button-group button.devui-btn-stress')
        await asyncio.sleep(5)

        await self.task_page.evaluate(
                '''() =>{ document.querySelector('div.step-body div.template-wraper div.mt10.ng-star-inserted button.devui-btn').click() }''')
        await asyncio.sleep(3)

        for i in range(1, 29):
            el = "#app-devcloud-frameworks > div > ng-component > ng-component > div > step-switcher > div > div.step-body.positon-relative > app-create-template-select > div > div.template-content > ul > li:nth-child(" + str(i) + ") > div > div.name.over-flow-ellipsis"
            title = await self.task_page.Jeval(el, "attr => attr.getAttribute('title')")
            if title == "空白构建模板":
                await self.task_page.click("#app-devcloud-frameworks > div > ng-component > ng-component > div > step-switcher > div > div.step-body.positon-relative > app-create-template-select > div > div.template-content > ul > li:nth-child(" + str(i) + ") > div > div.name.over-flow-ellipsis")
                break;

        # template = await self.task_page.querySelectorAll('.template-content li.template-item')
        # self.logger.info("选择空白构建")
        # await template[3].click()
        await asyncio.sleep(2)


        await self.task_page.click('.button-group .devui-btn-stress')
        await asyncio.sleep(5)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('div.task-detail-cardlist div:nth-child(3) div.btn-wrapper .add-btn').click() }''')
        await asyncio.sleep(3)
        # await self.task_page.click('.task-detail-cardlist .card-li:nth-child(3) .add-btn')
        # await asyncio.sleep(2)
        # await self.task_page.click('.button-group .devui-btn-stress')
        # await asyncio.sleep(3)
        # await self.task_page.click('#choisModels_new')
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > ng-component > div > edit > d-fullscreen > div > div > div.step-footer > div > d-button:nth-child(2) > button').click() }''')
        await asyncio.sleep(3)
        self.logger.info("执行构建")
        await asyncio.sleep(10)


    async def compile_build_task(self):
        await asyncio.sleep(5)
        try:
            node = 'div.devui-table-view tbody tr:nth-child(1) .operation-btn-section .devui-btn:nth-child(1)'
            await self.task_page.evaluate('''() =>{ document.querySelector('%s').click(); }''' % node)
            await asyncio.sleep(1)
        except Exception as e:
            self.logger.info(e)
            self.logger.info("已完成构建")
            return

            node = 'ul.devui-dropdown-menu li:nth-child(1) a'
            await self.task_page.evaluate('''() =>{ document.querySelector('%s').click(); }''' % node)
            await asyncio.sleep(2)
            # 修改时间：2021年10月15日14:55:31
            # await self.task_page.click('.modal-footer .devui-btn-primary')
            await self.task_page.click('#btn-confirm .devui-btn-primary')

        await asyncio.sleep(8)

    async def check_code_task(self):
        # await asyncio.sleep(5)
        # codecheckUrl = 'https://devcloud.cn-north-4.huaweicloud.com/codecheck/home'
        # await self.task_page.goto(codecheckUrl, {'waitUntil': 'load'})
        # await asyncio.sleep(5)
        # await self.task_page.click('#task_execute_phoenix-codecheck-worker')
        # await asyncio.sleep(5)


        # 原作者代码，修改爬取task-name对应的class，待测试
        task_list = await self.task_page.querySelectorAll('.devui-table tbody tr')
        task_id = await task_list[0].Jeval('.task-name', "el => el.getAttribute('id')")
        task_id = task_id.replace('task_name', 'task_execute')
        if await self.task_page.querySelector(f'#{task_id}'):
            await self.task_page.click(f'#{task_id}')
        else:
            btn_list = await self.task_page.querySelectorAll('.devui-btn-text-dark')
            await btn_list[0].click()
            await asyncio.sleep(1)
            await self.task_page.click(f'#{task_id}')
        await asyncio.sleep(5)

    async def week_new_deploy(self):
        await asyncio.sleep(2)
        await self.task_page.waitForSelector('.devui-layout-operate', {'visible': True})
        await self.task_page.click('.devui-layout-operate #taskCreate')
        await asyncio.sleep(1)
        await self.task_page.click('.step-group .devui-btn-stress')
        await asyncio.sleep(5)

        template_list = await self.task_page.querySelectorAll('.template-list .template-item')
        await template_list[1].click()
        await asyncio.sleep(0.5)
        await self.task_page.click('.step-group .devui-btn-stress')
        await asyncio.sleep(3)
        items = await self.task_page.querySelectorAll('.category-wrapper ul.devui-nav li')
        await items[4].click()
        await asyncio.sleep(3)

        card_list = await self.task_page.querySelectorAll('.task-detail-cardlist .card-li')
        await card_list[0].hover()
        await asyncio.sleep(0.5)
        await self.task_page.click('.task-detail-cardlist .card-li:nth-child(1) .add-btn')
        await asyncio.sleep(1)

        link_list = await self.task_page.querySelectorAll('.marked-text .devui-link')
        await link_list[1].click()

        await asyncio.sleep(10)
        page_list = await self.browser.pages()
        await page_list[-1].setViewport({'width': self.width, 'height': self.height})
        new_page = page_list[-1]
        await asyncio.sleep(2)
        await new_page.type('input.input-textarea-cn', self.username)
        await asyncio.sleep(0.5)
        await new_page.click('.btn-box .devui-btn-stress')
        await asyncio.sleep(2)
        await new_page.close()

        await self.task_page.click('#DeploymentGroup_groupId_button')
        await asyncio.sleep(2)
        await self.task_page.click('.deployment-select')
        await asyncio.sleep(0.5)
        await self.task_page.click('.devui-dropdown-item:nth-child(1)')
        await asyncio.sleep(0.5)
        await self.task_page.type('div#SingleLineText_port_to_stop input', ''.join(random.choices(string.digits, k=4)))
        await asyncio.sleep(0.5)
        await self.task_page.click('.deployman-create-content__button-group .devui-btn-primary')
        await asyncio.sleep(3)

    async def week_new_deploy_task(self):
        await asyncio.sleep(8)
        await self.task_page.click('#taskCreate')
        await asyncio.sleep(3)
        await self.task_page.evaluate(
            '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > div > create-new-form > div > div.deployman-create-warpper.position-relative > div.content-center > div > div > d-button.ng-star-inserted > button').click(); }''')
        await asyncio.sleep(2)
        await self.task_page.evaluate(
            '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > div > create-new-form > div > div.deployman-create-warpper.position-relative > div.content-center > div > choose-template > div.content > div > div > div:nth-child(2) > div.template-list > div:nth-child(1) > div').click(); }''')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
            '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > div > create-new-form > div > div.deployman-create-warpper.position-relative > div.content-center > div > div > d-button:nth-child(2) > button').click(); }''')
        await asyncio.sleep(3)
        await self.task_page.type('#app-devcloud-frameworks > div > ng-component > div > template-form > div > form > deploy-step > div > div.operation-box__plugins-list.ng-star-inserted > extend-plugins-render > div > div.task-detail-title.margin-bottom-20.fn-clear-float.plugin-titile > d-search > div > input', "shell")
        await asyncio.sleep(1)
        await self.task_page.evaluate(
            '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > div > template-form > div > form > deploy-step > div > div.operation-box__plugins-list.ng-star-inserted > extend-plugins-render > div > div.task-detail-title.margin-bottom-20.fn-clear-float.plugin-titile > d-search > div > span.devui-search-icon').click(); }''')
        await asyncio.sleep(3)
        await self.task_page.evaluate(
            '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > div > template-form > div > form > deploy-step > div > div.operation-box__plugins-list.ng-star-inserted > extend-plugins-render > div > extend-plugins-list > div.task-detail-cardlist.fn-clear-float > div:nth-child(1) > div.btn-wrapper > span').click(); }''')
        await asyncio.sleep(1)

        title_elements = await self.task_page.Jx('//*[@id="DeploymentGroup_groupId"]/label/div/div/span/span[3]/span/a')
        newHostGroupUrl = ""
        for item in title_elements:
            newHostGroupUrl = await (await item.getProperty('href')).jsonValue()
        
        page = await self.browser.newPage()
        await page.goto(newHostGroupUrl, {'waitUntil': 'load'})
        await asyncio.sleep(5)
        try:
            await page.type('#app-devcloud-frameworks > div > ng-component > div > hostgroup-info > div > d-tabs > div > div > basic-info > div > div > div:nth-child(1) > input', "linux")
            await asyncio.sleep(1)
            await page.evaluate(
                '''() =>{ document.querySelector('div.btn-box button.devui-btn-primary').click(); }''')
            await asyncio.sleep(3)
            await page.click("div.btn-group d-button:nth-child(2) button.devui-btn-primary")
            await asyncio.sleep(3)
            await page.type('#addHostDialog > div > div > d-modal-container > div > div > div > ng-component > div > div:nth-child(3) > div.ext-form-item-content > input', "linux")
            await asyncio.sleep(1)
            await page.type('#addHostDialog > div > div > d-modal-container > div > div > div > ng-component > div > div:nth-child(5) > div.ext-form-item-content > input', "" + self.serverIP)
            await asyncio.sleep(1)
            await page.type('#addHostDialog > div > div > d-modal-container > div > div > div > ng-component > div > div:nth-child(13) > div.ext-form-item-content > input', "user"+self.username)
            await asyncio.sleep(1)
            await page.type('#addHostDialog > div > div > d-modal-container > div > div > div > ng-component > div > div:nth-child(14) > div.ext-form-item-content > d-form-control > div.devui-form-control-container > input', self.password)
            await asyncio.sleep(1)
            await page.type('#addHostDialog > div > div > d-modal-container > div > div > div > ng-component > div > div:nth-child(15) > div.ext-form-item-content > input', "22")
            await asyncio.sleep(1)
            await page.evaluate(
                '''() =>{ document.querySelector('#addHostDialog > div > div > d-modal-container > div > div > div > ng-component > div > label > d-checkbox > div > label > span').click(); }''')
            await asyncio.sleep(1)
            await page.evaluate(
                '''() =>{ document.querySelector('#addHostDialog > div > div > d-modal-container > div > div > div > ng-component > div > div.button-container > d-button.mr10.ng-star-inserted > button').click(); }''')
            await asyncio.sleep(10)
        except Exception as e:
            self.logger.error(e)
            await page.close()
        finally:
            await page.close()

        # 刷新主机组
        await self.task_page.click("#DeploymentGroup_groupId_button")

        await self.task_page.evaluate(
            '''() =>{ document.querySelector('#DeploymentGroup_groupId > div > div.devui-form-group.devui-has-feedback > input').click(); }''')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
            '''() =>{ document.querySelector('#DeploymentGroup_groupId > div > div.devui-dropdown-menu.ng-trigger.ng-trigger-fadeInOut.ng-star-inserted > ul > ul > li').click(); }''')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
            '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > div > template-form > div > form > div.deployman-create-content__button-group.ng-star-inserted > d-button:nth-child(2) > button').click(); }''')
        await asyncio.sleep(1)

    async def deploy_task(self):
        await asyncio.sleep(3)
        # 修改时间：2021年10月15日15:01:51
        # await self.task_page.click('.devui-table tbody tr:nth-child(1) td:nth-child(6) #rf-task-execute')
        await self.task_page.click('#rf-task-execute')
        await asyncio.sleep(3)

    async def run_test(self):
        await self._close_test()
        await self.task_page.waitForSelector('div.devui-table-view', {'visible': True})
        # string = await self.task_page.Jeval('div.devui-table-view tbody tr:nth-child(1) td:nth-child(12)',
        #                                     'el => el.outerHTML')
        # print(string)

        await self.task_page.evaluate(
            '''() =>{ document.querySelector('div.devui-table-view tbody tr:nth-child(1) td:nth-child(12) i.icon-run').click(); }''')

        await asyncio.sleep(5)

    async def api_test_task(self):
        await asyncio.sleep(10)
        # await self._close_test()
        # await self._tab_api_test()
        await self.task_page.waitForSelector('#testdesign a', {'visible': True})
        await self.task_page.click("#testdesign a")
        await asyncio.sleep(10)

        await self.task_page.waitForSelector('#testtype_1', {'visible': True})
        await self.task_page.click("#testtype_1 a")
        await asyncio.sleep(5)

        await asyncio.sleep(8)
        # await self.task_page.evaluate(
        #     '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > ng-component > div > ng-component > new-test-design > div > d-splitter > d-splitter-pane.splitter-right.devui-splitter-pane > div > div > test-case-operations > div > div > div > d-button.mr4.ng-star-inserted > button').click(); }''')
        # await asyncio.sleep(2)
        # await self.task_page.type('#caseName', ''.join(random.choices(string.ascii_letters, k=6)))
        # await asyncio.sleep(1)
        # await self.task_page.evaluate(
        #     '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > ng-component > div > ng-component > new-test-design > div > d-splitter > d-splitter-pane.splitter-right.devui-splitter-pane > div > div > test-case-operations > div.add-container.ng-star-inserted > create-test-suite > div > div > div > form > div.ts-form-content-left > div.mt-10.ng-star-inserted > suite-case > div > div.no-data-tips.ng-star-inserted > div > span.addNow').click(); }''')
        # await asyncio.sleep(3)
        # await self.task_page.type('#modal-modal > div > div > ng-component > div > div.modal-body > div.listBody.clearBoth > d-splitter > d-splitter-pane:nth-child(2) > div.clear-fix.clearBoth > d-search > div > input', "10010")
        # await asyncio.sleep(1)
        # await self.task_page.evaluate(
        #     '''() =>{ document.querySelector('#modal-modal > div > div > ng-component > div > div.modal-body > div.listBody.clearBoth > d-splitter > d-splitter-pane:nth-child(2) > div.clear-fix.clearBoth > d-search > div > span.devui-search-icon.devui-search-icon-sm').click(); }''')
        # await asyncio.sleep(3)
        # await self.task_page.evaluate(
        #     '''() =>{ document.querySelector('#modal-modal > div > div > ng-component > div > div.modal-body > div.listBody.clearBoth > d-splitter > d-splitter-pane:nth-child(2) > div.add-case-list-wrap > mutual-item-list > div.data-list > d-data-table > div > div > div > table > tbody > tr > td.devui-checkable-cell > d-checkbox > div > label > span').click(); }''')
        # await asyncio.sleep(1)
        # await self.task_page.evaluate(
        #     '''() =>{ document.querySelector('#modal-modal > div > div > ng-component > div > div.modal-body > div.modal-footer > d-button:nth-child(1) > button').click(); }''')
        # await asyncio.sleep(3)
        # await self.task_page.evaluate(
        #     '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > ng-component > div > ng-component > new-test-design > div > d-splitter > d-splitter-pane.splitter-right.devui-splitter-pane > div > div > test-case-operations > div.add-container.ng-star-inserted > create-test-suite > div > div > div > div.confirmBtn > d-button.ave-button-margin-right > button').click(); }''')
        # await asyncio.sleep(3)
        await self.task_page.evaluate(
            '''() =>{ document.querySelector('#table-list > div > operate-item-list > div.data-list > d-data-table > div > div > div > table > tbody > tr > td.cell-nowrap.devui-sticky-right-cell.ng-star-inserted > div > operate-info > div > i.icon.icon-run.ng-star-inserted').click(); }''')
        await asyncio.sleep(5)

    async def week_new_pipeline(self):
        await asyncio.sleep(5)
        await self.task_page.waitForSelector('#createPipeline', {'visible': True})
        await self.task_page.click('#createPipeline')
        await asyncio.sleep(2)
        await self.task_page.click('#echoTestNextStep')
        await asyncio.sleep(2)
        await self.task_page.click('div.content span.button-content')
        await asyncio.sleep(2)

        for i in range(1, 8):
            el = "#app-devcloud-frameworks > div > ng-component > ng-component > div > div.content > select-template > div > div > div > div > div:nth-child(" + str(i) + ") > div > div.template-content > div"
            title = await self.task_page.Jeval(el, "attr => attr.getAttribute('title')")
            if title == "空白模板":
                await self.task_page.click(el)
                break;

        # await self.task_page.evaluate(
        #     '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > ng-component > div > div.content > select-template > div > div.select-template-content > div.template-item.dontUse > div.template-content > div.template-title.over-flow-ellipsis').click(); }''')
        # await asyncio.sleep(1)
        await self.task_page.click('#echoTestButtonOk')
        await asyncio.sleep(5)
        await self.task_page.click('#pipeline_task_btn_save_run')
        await asyncio.sleep(5)

        # dropdowns = await self.task_page.querySelectorAll('.devui-dropup')
        # for dropdown in dropdowns:
        #     await dropdown.click()
        #     await asyncio.sleep(1)
        #     dropdown_item = await dropdown.querySelectorAll('.devui-dropdown-item')
        #     await dropdown_item[0].click()
        #     await asyncio.sleep(1)

        # await self.task_page.click('.pipeline-edit-tab .devui-btn-primary')
        # await asyncio.sleep(1)
        # await self.task_page.click('.pipeline-edit-tab .devui-btn-primary')
        # await asyncio.sleep(5)

    async def pipeline_task(self):
        items = await self.task_page.querySelectorAll('div.devui-table-view tbody tr')
        if len(items) <= 0:
            return

        await self.task_page.evaluate(
            '''() =>{ document.querySelector('div.devui-table-view tbody tr:nth-child(1) .devui-btn-default').click(); }''')
        await asyncio.sleep(1)

        await self.task_page.click('#OctopusExecute .devui-btn-primary')
        await asyncio.sleep(3)
        await self.task_page.click('#startPipeBtn .devui-btn-primary')
        await asyncio.sleep(1)

        # dropdowns = await self.task_page.querySelectorAll('div.source-value')
        # dropup = await dropdowns[0].querySelectorAll('.devui-dropup')
        # await dropup[1].click()
        # await asyncio.sleep(2)
        # dropdown_item = await dropup[1].querySelectorAll('.devui-dropdown-item')
        # await dropdown_item[0].click()
        # await asyncio.sleep(0.5)
        # await self.task_page.click('.modal.in .devui-btn-primary')
        await asyncio.sleep(5)

    async def week_new_project(self):
        await asyncio.sleep(5)
        try:
            notice = await self.task_page.querySelector('#declaration-notice')
            if notice:
                btn_list = await self.task_page.querySelectorAll('.quick-create-phoenix .devui-btn')
                await btn_list[1].click()
                await asyncio.sleep(1)
                await self.task_page.click('#declaration-notice div.devui-checkbox label')
                await asyncio.sleep(1)
                await self.task_page.click('#declaration-notice .devui-btn.devui-btn-primary')
                await asyncio.sleep(1)
        except Exception as e:
            self.logger.debug(e)

        try:
            btn_list = await self.task_page.querySelectorAll('.quick-create-phoenix .devui-btn')
            await btn_list[0].click()
            await asyncio.sleep(2)
        except Exception as e:
            self.logger.exception(e)
            await self.close()
            self.cancel = True

    async def week_new_git(self):
        await asyncio.sleep(5)
        no_data = await self.task_page.querySelector('.new-list .no-data')
        await self.task_page.waitForSelector('.pull-right', {'visible': True})
        await self.task_page.click('.toolbar-wrapper .devui-btn-primary')
        await asyncio.sleep(3)
        git_name = ''.join(random.choices(string.ascii_letters, k=6))
        if not no_data:
            git_name = 'crawler'
        await self.task_page.type('#rname', git_name)
        await asyncio.sleep(0.5)

        btn_list = await self.task_page.querySelectorAll('.new-repo-row-center:nth-child(1) .devui-checkbox')
        await btn_list[2].click()

        await self.task_page.click('#newAddRepoBtn')
        await asyncio.sleep(8)

        git_list = await self.task_page.querySelectorAll('.devui-table tbody tr')
        if git_list and len(git_list) and git_name == 'crawler':
            await self.task_page.click('#repoNamecrawler')
            await asyncio.sleep(10)
            git_url = await self.task_page.Jeval('.clone-url span', "el => el.getAttribute('title')")
            _user = self.parent_user if self.parent_user else self.username
            git_url = git_url.replace('git@', f'https://{_user}%2F{self.username}:{self.password}@')
            self.git = git_url.replace('com:', 'com/')
            self.logger.info(self.git)

    async def week_new_code_check(self):
        await self.task_page.waitForSelector('.pull-right', {'visible': True})
        await self.task_page.click('.pull-right .devui-btn-primary')
        await asyncio.sleep(8)
        btn = await self.task_page.querySelector('#codecheck-new-task-btn-0')
        if btn:
            await btn.click()
            await asyncio.sleep(1)
            await self.task_page.click('.btn-wrap .devui-btn-primary')
            await asyncio.sleep(5)

    async def upload_task(self):
        await asyncio.sleep(3)
        # items = await self.task_page.querySelectorAll('')

        await self.task_page.click('#releasemanUploadDrop tbody tr:nth-child(1) td a.column-link')
        await asyncio.sleep(3)
        await self.task_page.waitForSelector('#upload_file', {'visible': True})
        f = await self.task_page.querySelector('#releaseman-file-select')
        await f.uploadFile(__file__)
        await asyncio.sleep(3)

    async def new_test_task(self):
        await asyncio.sleep(15)
        try:
            await self.task_page.click('#global-guidelines .icon-close')
        except Exception as e:
            self.logger.debug(e)

        await asyncio.sleep(1)

        try:
            await self.task_page.click('.guide-container .icon-close')
        except Exception as e:
            self.logger.debug(e)

        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > ng-component > div > ng-component > new-test-design > div > d-splitter > d-splitter-pane.splitter-right.devui-splitter-pane > div > div > test-case-operations > div > div > div.create-case > d-button > button').click() }''')
        await asyncio.sleep(2)

        await asyncio.sleep(1)
        await self.task_page.waitForSelector('div.create-case', {'visible': True})
        await self.task_page.click('div.create-case button.devui-btn.devui-btn-primary.devui-btn-md.devui-btn-default')
        await asyncio.sleep(5)
        caseName = ''.join(random.choices(string.ascii_letters, k=6))
        await self.task_page.type('#caseName', caseName)
        await asyncio.sleep(2)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('div.footer > d-button.ave-button-margin-right > button').click() }''')
        self.logger.info("保存")
        await asyncio.sleep(5)

    async def run_test_task(self):
        await asyncio.sleep(15)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > ng-component > div > ng-component > new-test-design > div > d-splitter > d-splitter-pane.splitter-right.devui-splitter-pane > div > div > test-case-operations > div > div > div > d-button.mr4.ng-star-inserted > button').click() }''')
        await asyncio.sleep(2)
        await self.task_page.type('#caseName', ''.join(random.choices(string.ascii_letters, k=6)))
        await asyncio.sleep(1)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > ng-component > div > ng-component > new-test-design > div > d-splitter > d-splitter-pane.splitter-right.devui-splitter-pane > div > div > test-case-operations > div.add-container.ng-star-inserted > create-test-suite > div > div > div > form > div.ts-form-content-left > div.case-content.ng-star-inserted > div > div > div.ng-star-inserted > div > span.addNow').click() }''')
        await asyncio.sleep(5)
        await self.task_page.type('#add-case-to-suite div.modal-body div.listBody.clearBoth d-splitter-pane:nth-child(2) .devui-search input.devui-input.devui-input-sm', '108')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#add-case-to-suite > div > div > ng-component > div > div.modal-body > div.listBody.clearBoth > d-splitter > d-splitter-pane:nth-child(2) > div.clear-fix.clearBoth > d-search > div > span.devui-search-icon.devui-search-icon-sm').click() }''')
        await asyncio.sleep(3)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#add-case-to-suite > div > div > ng-component > div > div.modal-body > div.listBody.clearBoth > d-splitter > d-splitter-pane:nth-child(2) > div.add-case-list-wrap > mutual-item-list > div.data-list > d-data-table > div > div > div > table > tbody > tr:nth-child(1) > td.devui-checkable-cell > d-checkbox > div > label > span').click() }''')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#add-case-to-suite > div > div > ng-component > div > div.modal-body > div.modal-footer > d-button:nth-child(1) > button').click() }''')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#app-devcloud-frameworks > div > ng-component > ng-component > div > ng-component > new-test-design > div > d-splitter > d-splitter-pane.splitter-right.devui-splitter-pane > div > div > test-case-operations > div.add-container.ng-star-inserted > create-test-suite > div > div > div > div.confirmBtn > d-button.ave-button-margin-right > button').click() }''')
        await asyncio.sleep(3)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#operate_serviceType > i.icon.icon-run.ng-star-inserted').click() }''')
        await asyncio.sleep(3)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#tsStepReadonlyId > form > div.execute-column > div.execute-column-right.ng-star-inserted > form > div:nth-child(3) > div.left > div > d-select > div > div.devui-form-group.devui-has-feedback > span').click() }''')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#tsStepReadonlyId > form > div.execute-column > div.execute-column-right.ng-star-inserted > form > div:nth-child(3) > div.left > div > d-select > div > div.devui-dropdown-menu.ng-trigger.ng-trigger-fadeInOut.ng-star-inserted > ul > ul > li:nth-child(2)').click() }''')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#tsStepReadonlyId > form > div.execute-column > div.execute-column-right.ng-star-inserted > form > div:nth-child(3) > div.right > d-button:nth-child(1) > button').click() }''')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#title-fixed > div.set-suite-result > div.mr-20 > d-select > div > div.devui-form-group.devui-has-feedback > span').click() }''')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#title-fixed > div.set-suite-result > div.mr-20 > d-select > div > div.devui-dropdown-menu.ng-trigger.ng-trigger-fadeInOut.ng-star-inserted > ul > ul > li:nth-child(2)').click() }''')
        await asyncio.sleep(2)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#title-fixed > div.right.pt-size > d-button > button').click() }''')
        await asyncio.sleep(1)


    async def week_new_api_test_task(self):
        await asyncio.sleep(15)
        # await self._close_test()
        # await self._tab_api_test()
        # self.logger.info(self.task_page.url)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#testtype_1 > a').click() }''')
        await asyncio.sleep(8)

        # await self.task_page.evaluate(
        #         '''() =>{ document.querySelector('div.create-case d-button').click() }''')
        # await asyncio.sleep(3)

        await self.task_page.waitForSelector('div.create-case', {'visible': True})
        await self.task_page.click('div.create-case d-button')
        await asyncio.sleep(2)
        caseName = ''.join(random.choices(string.ascii_letters, k=6))
        await self.task_page.type('#caseName', caseName)
        await asyncio.sleep(1)
        await self.task_page.type('#description', 'Description ' + caseName)
        await asyncio.sleep(1)
        await self.task_page.type('#preparation', 'Preparation ' + caseName)
        await asyncio.sleep(1)
        await self.task_page.type('#testStep', 'TestStep ' + caseName)
        await asyncio.sleep(1)
        await self.task_page.type('#expectResult', 'ExpectResult ' + caseName)
        await asyncio.sleep(1)
        await self.task_page.type('#caseNo', '11111')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('div.content-right div:nth-child(8) a.issue-name').click() }''')
        await asyncio.sleep(5)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('div.modal-body div.devui-table-view table tbody tr:nth-child(1) td:nth-child(1) span.devui-radio-material').click() }''')
        await asyncio.sleep(1)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('div.modal-footer d-button:nth-child(1) button').click() }''')
        await asyncio.sleep(3)

        await self.task_page.click('div.footer d-button:nth-child(2) button.devui-btn-stress span')
        self.logger.info("保存")
        await asyncio.sleep(3)
        # self.logger.info(self.task_page.url)

    async def remove_api_task(self):
        # 进入控制台
        try:
            await self.task_page.evaluate(
                '''() =>{ document.querySelector('#overViewContent > div.pr > div.cti-clearfix.h341.sceneHeader > div.overview-console-btn > div:nth-child(2) > span > button > span').click() }''')
            await asyncio.sleep(2)
            self.logger.info('进入控制台概览')
            await self.task_page.evaluate(
                    '''() =>{ document.querySelector('#overViewContent > div.overviewCenter > div.pull-left.overviewPhysical > div.my-resource > div.cti-row.cti-cardlist > div:nth-child(2) > div').click() }''')
            await asyncio.sleep(2)
            self.logger.info('进入API管理')
        except Exception as e:
            self.logger.info('none')
            await asyncio.sleep(2)

        await self.task_page.evaluate(
            '''() =>{ document.querySelector('#openapi_list > tbody > tr > td:nth-child(2) > div > div:nth-child(1) > a').click() }''')
        await asyncio.sleep(3)
        self.logger.info("选择API")

        try:
            await self.task_page.click("#offlineAPI")
            await asyncio.sleep(1)
            self.logger.info("下线API")
            await self.task_page.evaluate(
                '''() =>{ document.querySelector('body > div.ti-modal.ti-fade.ng-isolate-scope.ti-in > div > div > div > div.ti-modal-footer > div:nth-child(1) > span > button').click() }''')
            await asyncio.sleep(1)
            self.logger.info("确认下线API")
        except Exception as e:
            self.logger.info("已下线API")
            await asyncio.sleep(1)
            # raise e

        await self.task_page.click("#api_detail_refresh")
        await asyncio.sleep(2)
        self.logger.info('刷新页面')

        try:
            await self.task_page.click("#deleteAPI")
            await asyncio.sleep(1)
            self.logger.info("删除API")
            await self.task_page.type("#deleteContent-text", "DELETE")
            await asyncio.sleep(1)
            self.logger.info("输入DELETE")
            await self.task_page.evaluate(
                '''() =>{ document.querySelector('body > div.ti-modal.ti-fade.ng-isolate-scope.ti-in > div > div > div.ti-modal-footer.ng-scope > div:nth-child(1) > span > button').click() }''')
            await asyncio.sleep(1)
            self.logger.info("确认删除API")
        except Exception as e:
            self.logger.info("已删除API")
            # raise e
        await asyncio.sleep(5)


        await asyncio.sleep(1)
        

        try:
            await self.task_page.evaluate(
                '''() =>{ document.querySelector('#apig_multiLogical_openapi_group > span').click() }''')
            await asyncio.sleep(5)
            self.logger.info("进入API分组")
            await self.task_page.click("#deletegroup")
            await asyncio.sleep(1)
            self.logger.info("删除API分组")
            await self.task_page.type("#tiny-text", "DELETE")
            await asyncio.sleep(1)
            self.logger.info("输入DELETE")
            await self.task_page.click("#delG")
            await asyncio.sleep(1)
            self.logger.info("确认删除API分组")
        except Exception as e:
            self.logger.info("已删除API分组")
            # raise e

        await asyncio.sleep(3)

    async def new_new_api_task(self):
        await asyncio.sleep(15)
        # 调试API
        try:
            await self.task_page.evaluate(
                '''() =>{ document.querySelector('#contentcontent_fugwff > div:nth-child(2) > div.ac-cloud-content > div > div.create-header-content > div.ac-pdTop-lg.ac-pdBottom-lg.ac-pdLeft-lg.ac-pdRight-lg > div > span > button').click() }''')
            await asyncio.sleep(3)
            await self.task_page.evaluate(
                '''() =>{ document.querySelector('body > div.ti-intro-tip-flag.ng-isolate-scope.ti-tooltip.ti-intro-tip-modal.ti-tooltip-top-left > div.ti-tooltip-content.ti-intro-tooltip-content.ng-scope > ti-intro-content > div > div.ti-modal-footer > div > button').click() }''')
            await asyncio.sleep(3)
        except Exception as e:
            self.logger.info('none')
            await asyncio.sleep(2)
        # await self.task_page.click('div.ti-modal-header ti-close')
        # await asyncio.sleep(1)
        urlHeader = self.task_page.url.split("groupDetail")
        self.logger.info(urlHeader)
        await self.task_page.goto(urlHeader[0] + "multiLogical/openapi/list", {'waitUntil': 'load'})
        await asyncio.sleep(8)
        controlUrl = self.task_page.url
        self.logger.info(controlUrl)
        # await self.remove_api_task()

    async def run_api_task(self):
        await asyncio.sleep(3)
        await self.task_page.click('div.ti-intro-modal .ti-btn-danger')
        await asyncio.sleep(3)
        await self.task_page.click('#send')
        await asyncio.sleep(2)
        await self.task_page.click('.pull-left .cti-button')
        await asyncio.sleep(5)
        await self.task_page.click('.pull-right.mr10.cti-button')
        await asyncio.sleep(5)
        await self.task_page.click('.ti-btn-danger.ml10.ng-binding')

    async def debug_api_task(self):
        await asyncio.sleep(5)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#overViewContent > div.cti-clearfix > div.cti-fl-right > div:nth-child(1) > span > button').click() }''')
        await asyncio.sleep(10)
        keyName = self.task_page.url.split('/')
        if keyName[6] == 'expdemo':
            await self.task_page.evaluate(
                '''() =>{ document.querySelector('#contentcontent_fugwff > div:nth-child(2) > div.ac-cloud-content > div > div.create-header-content > div.ac-pdTop-lg.ac-pdBottom-lg.ac-pdLeft-lg.ac-pdRight-lg > div > span > button').click() }''')
            await asyncio.sleep(5)
            await self.task_page.evaluate(
                    '''() =>{ document.querySelector('#send').click() }''')
            await asyncio.sleep(3)
        elif keyName[9] == 'apilist':
            await self.task_page.evaluate(
                '''() =>{ document.querySelector('body > div.ti-intro-tip-flag.ng-isolate-scope.ti-tooltip.ti-intro-tip-modal.ti-tooltip-top-left > div.ti-tooltip-content.ti-intro-tooltip-content.ng-scope > ti-intro-content > div > div.ti-modal-footer > div > button').click() }''')
            await asyncio.sleep(5)
            await self.task_page.evaluate(
                    '''() =>{ document.querySelector('#send').click() }''')
            await asyncio.sleep(3)

        
        await self.new_new_api_task()

    async def new_fun_task(self):
        url = self.task_page.url
        if url.find('serverless/dashboard') == -1:
            url = f'{url}#/serverless/dashboard'
            await self.task_page.goto(url, {'waitUntil': 'load'})

        await asyncio.sleep(2)
        try:
            await self.task_page.click('#rightWrap .ant-row .ant-btn')
            await asyncio.sleep(3)
            await self.task_page.type('#name', ''.join(random.choices(string.ascii_letters, k=6)), {'delay': 30})
            await asyncio.sleep(3)
            await self.task_page.click('.preview .ant-btn-primary')
            await asyncio.sleep(5)
        except Exception as e:
            self.logger.warning(e)
        finally:
            return

    async def fast_dev_star(self):
        await asyncio.sleep(5)
        await self.task_page.click('.code-template-codebase-right-operations-panel .devui-btn-common')
        # await asyncio.sleep(1)
        # await self.task_page.click('.operation-next')
        await asyncio.sleep(3)
        await self.task_page.click('#deploy-btn')

        await asyncio.sleep(15)

    async def get_address(self):
        page = await self.browser.newPage()
        url = 'https://devcloud.huaweicloud.com/bonususer/v2/address/queryPageList?page_no=1&page_size=5&_=1620962399910'
        res = await page.goto(url, {'waitUntil': 'load'})
        try:
            data = await res.json()
            if data.get('error') or not data.get('result'):
                await asyncio.sleep(1)
                return ''
            address = data.get('result').get('result')
            if type(address) == list:
                address = address[0]
                return address.get('id')
        except Exception as e:
            self.logger.error(e)
        finally:
            await page.close()
        return ''

    async def delete_function(self):
        page = await self.browser.newPage()

        url_list = ['https://console.huaweicloud.com/functiongraph/?region=cn-south-1#/serverless/functionList',
                    'https://console.huaweicloud.com/functiongraph/?region=cn-north-4#/serverless/functionList']

        for _url in url_list:
            await page.goto(_url, {'waitUntil': 'load'})
            await page.setViewport({'width': self.width + 560, 'height': self.height})
            try:
                await page.waitForSelector('.ti3-action-menu-item', {'timeout': 10000})
            except Exception as e:
                self.logger.debug(e)
                continue

            while 1:
                elements = await page.querySelectorAll('td[style="white-space: normal;"]')
                if not elements or not len(elements):
                    self.logger.info('no functions.')
                    break

                a_list = await elements[0].querySelectorAll('a.ti3-action-menu-item')
                # content = str(await (await element.getProperty('textContent')).jsonValue()).strip()
                if len(a_list) == 2:
                    try:
                        await a_list[1].click()
                        await asyncio.sleep(1)

                        _input = await page.querySelector('.modal-confirm-text input[type="text"]')
                        if not _input:
                            await asyncio.sleep(3)
                            continue

                        await page.type('.modal-confirm-text input[type="text"]', 'DELETE')
                        await asyncio.sleep(1)
                        await page.click('.ti3-modal-footer .ti3-btn-danger')
                        await asyncio.sleep(1)

                        buttons = await page.querySelectorAll('.ti3-modal-footer [type="button"]')
                        if buttons and len(buttons):
                            await buttons[1].click()
                            await asyncio.sleep(2)

                    except Exception as e:
                        self.logger.debug(e)
                        await asyncio.sleep(1)

            await asyncio.sleep(1)

        await page.close()
        await asyncio.sleep(1)

    async def check_project(self):
        page = await self.browser.newPage()
        domains = ['https://devcloud.huaweicloud.com', 'https://devcloud.cn-north-4.huaweicloud.com']
        try:
            for domain in domains:
                url = f'{domain}/projects/v2/project/list?sort=&search=&page_no=1&page_size=40&project_type=&archive=1'
                res = await page.goto(url, {'waitUntil': 'load'})
                data = await res.json()
                if data.get('error') or not data.get('result'):
                    await asyncio.sleep(1)
                    continue

                projects = data['result']['project_info_list']
                self.home_url = domain

                if len(projects) > 0:
                    self.create_done = False
                    break
                await asyncio.sleep(1)
        except Exception as e:
            self.logger.error(e)
        finally:
            await page.close()
            self.logger.info(self.create_done)

    async def delete_project(self):
        page = await self.browser.newPage()
        domains = ['https://devcloud.huaweicloud.com', 'https://devcloud.cn-north-4.huaweicloud.com']
        for i in range(3):
            try:
                for domain in domains:
                    url = f'{domain}/projects/v2/project/list?sort=&search=&page_no=1&page_size=40&project_type=&archive=1'
                    res = await page.goto(url, {'waitUntil': 'load'})
                    data = await res.json()
                    if data.get('error') or not data.get('result'):
                        continue

                    for item in data['result']['project_info_list']:
                        try:
                            self.logger.warning(f"delete project {item['name']}")
                            delete_url = f"{domain}/projects/project/{item['project_id']}/config/info"
                            await page.goto(delete_url, {'waitUntil': 'load'})
                            await asyncio.sleep(2)
                            btn_list = await page.querySelectorAll('.modal-footer .btn')
                            if len(btn_list) == 2:
                                await btn_list[1].click()
                                await asyncio.sleep(1)

                            await page.click('.form-container .margin-right-s .devui-btn:nth-child(1)')
                            await asyncio.sleep(2)
                            await page.type('#deleteProject .projectInput', item['name'])
                            await asyncio.sleep(0.5)
                            await page.click('.dialog-footer .devui-btn-primary')
                            await asyncio.sleep(1)
                        except Exception as e:
                            self.logger.error(e)
                break
            except Exception as e:
                self.logger.error(e)
                await asyncio.sleep(5)
        await page.close()

    async def delete_api(self):
        page = await self.browser.newPage()
        try:
            await page.goto('https://console.huaweicloud.com/apig/?region=cn-north-4#/apig/multiLogical/openapi/list',
                            {'waitUntil': 'load'})
            await page.setViewport({'width': self.width, 'height': self.height})
            await asyncio.sleep(10)
            elements = await page.querySelectorAll('#openapi_list tr')
            if len(elements) < 2:
                return

            # 下线
            await page.click('#openapi_list tr:nth-child(1) th:nth-child(1)')
            await asyncio.sleep(0.5)
            await page.click('.apiList-groups .cti-button:nth-child(3) .cti-btn-container')
            await asyncio.sleep(1)
            await page.click('.ti-modal-dialog .cti-button:nth-child(1) .cti-btn-container')
            await asyncio.sleep(2)

            # 删除
            await page.click('#openapi_list tr:nth-child(1) th:nth-child(1)')
            await asyncio.sleep(0.5)
            await page.click('.apiList-groups .cti-button:nth-child(4) .cti-btn-container')
            await asyncio.sleep(3)
            await page.type('#deleteContent-text', 'DELETE')
            await asyncio.sleep(0.5)
            await page.click('.ti-modal-dialog .cti-button:nth-child(1) .cti-btn-container')
            await asyncio.sleep(2)
        except Exception as e:
            self.logger.debug(e)
        finally:
            await page.close()

    async def print_credit(self, user_name):
        new_credit = await self.get_credit()
        self.logger.info(f'码豆: {new_credit}')
        message = f'{user_name} -> {new_credit}'
        self.dingding_bot(message, '华为云码豆')
        self.pushPlusSend(self.resultsJSON, '华为云码豆')

    async def delete_api_group(self):
        page = await self.browser.newPage()
        try:
            await page.goto('https://console.huaweicloud.com/apig/?region=cn-north-4#/apig/multiLogical/openapi/group',
                            {'waitUntil': 'load'})
            await page.setViewport({'width': self.width, 'height': self.height})
            await asyncio.sleep(8)
            elements = await page.querySelectorAll('#openapi_group tbody tr')
            if len(elements) < 1:
                return

            await page.click('#openapi_group tbody tr:nth-child(1) td:nth-child(1) a')
            await asyncio.sleep(2)
            await page.click('.cti-fl-right .cti-button:nth-child(4) .cti-btn-container')
            await asyncio.sleep(1)
            await page.type('#tiny-text', 'DELETE')
            await asyncio.sleep(0.5)
            await page.click('#delG')
            await asyncio.sleep(2)
        except Exception as e:
            self.logger.debug(e)
        finally:
            await page.close()

    async def _close_test(self):
        try:
            await asyncio.sleep(1)
            await self.task_page.click('#global-guidelines .icon-close')
            await asyncio.sleep(2)
            await self.task_page.click('.guide-container .icon-close')
            await asyncio.sleep(1)
        except Exception as e:
            self.logger.debug(e)

    async def _tab_api_test(self):
        await asyncio.sleep(1)
        await self.task_page.waitForSelector('#testtype_1')
        await self.task_page.click('#testtype_1')
        await asyncio.sleep(2)

    async def sign_post(self):
        tid_list = [87703, 87513, 87948, 87424, 87445, 87587, 87972, 87972]
        n = random.randint(1, 2)
        for i in range(n):
            tid = random.choice(tid_list)
            await self.page.goto(f'https://bbs.huaweicloud.com/forum/thread-{tid}-1-1.html', {'waitUntil': 'load'})
            await self.page.waitForSelector('#fastpostsubmit')
            content = random.choice(
                ['666', '回帖送码豆', '论坛回帖送码豆喽'])
            await self.page.evaluate(
                '''() =>{ ue.setContent('<p>%s</p>'); }''' % content)
            await asyncio.sleep(1)
            await self.page.click('#fastpostsubmit')
            await asyncio.sleep(5)

    async def post_reply(self):
        await self.page.goto('https://bbs.huaweicloud.com/forum/thread-89722-1-1.html', {'waitUntil': 'load'})
        await self.page.waitForSelector('#fastpostsubmit')
        content = '#2020年终盛典# 我很期待这次盛典，祝盛典圆满成功！顺利召开！'
        await self.page.evaluate(
            '''() =>{ ue.setContent('<p>%s</p>'); }''' % content)
        await asyncio.sleep(1)
        await self.page.click('#fastpostsubmit')
        await asyncio.sleep(10)

        await self.page.goto('https://bbs.huaweicloud.com/forum/thread-89742-1-1.html', {'waitUntil': 'load'})
        await self.page.waitForSelector('#fastpostsubmit')
        content = ' #我和华为云的这一年#这一年是我和华为云相识的第一年，知道了华为云有很多课程，大拿讲课，受益颇丰。'
        await self.page.evaluate(
            '''() =>{ ue.setContent('<p>%s</p>'); }''' % content)
        await asyncio.sleep(1)
        await self.page.click('#fastpostsubmit')
        await asyncio.sleep(5)

        # await self.page.goto('https://bbs.huaweicloud.com/forum/thread-80376-1-1.html', {'waitUntil': 'load'})
        # await self.page.waitForSelector('#fastpostsubmit')
        # await self.page.evaluate('''() =>{ document.querySelector('#tabeditor-2').click(); }''')
        # await asyncio.sleep(1)
        # await self.page.click('#tabeditor-2')
        # content = random.choice(
        #     [
        #         '![1024](https://bbs-img-cbc-cn.obs.cn-north-1.myhuaweicloud.com/data/attachment/forum/202010/09/204951b8y0xls2nopvc6az.png)',
        #         '![1024](https://bbs-img-cbc-cn.obs.cn-north-1.myhuaweicloud.com/data/attachment/forum/202010/09/161504wwp2tknsrfkzytrm.png)',
        #         '![1024](https://bbs-img-cbc-cn.obs.cn-north-1.myhuaweicloud.com/data/attachment/forum/202010/09/173512tnrpfkysqadqtlee.png)',
        #         '![1024](https://bbs-img-cbc-cn.obs.cn-north-1.myhuaweicloud.com/data/attachment/forum/202010/09/162825q3widemjdlppcjb0.png)',
        #         '![1024](https://bbs-img-cbc-cn.obs.cn-north-1.myhuaweicloud.com/data/attachment/forum/202010/10/111533ab4neej10wtrbmm6.png)',
        #     ])
        # await self.page.type('.textarea', content, {'delay': 30})
        # # await self.page.evaluate('''() =>{ document.querySelector('.textarea').value = '%s'; }''' % content)
        # # await self.page.evaluate('''() =>{ document.querySelector('#mditorBox').value = '%s'; }''' % content)
        # await asyncio.sleep(1)
        # await self.page.click('#fastpostsubmit')
        # await asyncio.sleep(5)

    # 每周添加成员  需要建一个IAM子账户
    async def week_new_member(self):
        # await self.page.goto('https://devcloud.huaweicloud.com/bonususer/home/makebonus', {'waitUntil': 'load'})
        await asyncio.sleep(10)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#app-devcloud-frameworks > div.devui-layout.devui-layout-projects > ng-component > div > div > div.projects-container.margin-top-l > projects-board-in-home > div > a:nth-child(1) > div.name.over-flow-ellipsis').click() }''')
        await asyncio.sleep(10)
        # nowUrl = self.task_page.url.split("/")
        # self.logger.info(nowUrl[5])
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#config > a').click() }''')
        await asyncio.sleep(10)
        # 添加成员
        # 点击“添加成员”
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#add-member').click() }''')
        await asyncio.sleep(1)

        # 检查是否已添加
        trList = await self.task_page.querySelectorAll("table tbody tr")
        if len(trList) >= 2:
            self.logger.info("该项目已添加成员")
            return

        # 点击“从本企业用户”
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#cdk-overlay-0 > div > ul > li:nth-child(1) > a').click() }''')
        await asyncio.sleep(1)
        # 选择成员
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#memberModal > div > div > ng-component > div > select-member > div > d-tabs > div > div > d-data-table > div > div > div > table > tbody > tr > td.devui-checkable-cell.ng-star-inserted > d-checkbox > div > label').click() }''')
        await asyncio.sleep(1)
        # 点击“下一步”
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#memberModal > div > div > ng-component > div > div.add-member-btn > d-button.ng-star-inserted > button').click() }''')
        await asyncio.sleep(1)
        # 点击“保存”
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#memberModal > div > div > ng-component > div > div.add-member-btn > d-button:nth-child(2) > button').click() }''')
        await asyncio.sleep(3)

    # # 每天新建工作项
    async def new_work_project(self):
        # await self.page.goto('https://devcloud.huaweicloud.com/bonususer/home/makebonus', {'waitUntil': 'load'})
        await asyncio.sleep(10)
        self.logger.info(self.task_page.url)
        await asyncio.sleep(5)
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#app-devcloud-frameworks > div.devui-layout.devui-layout-projects > ng-component > div > div > div.projects-container.margin-top-l > projects-board-in-home > div > a:nth-child(1) > div.name.over-flow-ellipsis').click() }''')
        await asyncio.sleep(5)
        # 点击“新建”
        await self.task_page.click('#scrum-issue-dropdown')
        await asyncio.sleep(1)
        # 点击“BUG”
        await self.task_page.click('#newScrum_bug')
        await asyncio.sleep(1)
        # 标题添加时间戳
        nowTime = time.strftime('%Y-%m-%d %H:%M:%S')
        await self.task_page.type('#textArea', nowTime)
        await asyncio.sleep(1)
        # 保存
        await self.task_page.evaluate(
                '''() =>{ document.querySelector('#scrum-rightContent > ng-component > div.scrum-task-detail-footer.ng-star-inserted > d-button:nth-child(1) > button').click() }''')
        await asyncio.sleep(3)

