<?php
/**
 * Plugin Name: MTDL PCM Feed
 * Description: Exibe um feed de versão em https://seusite/version.json e fornece um shortcode [pcm_download_button]. Integração opcional com assinaturas (WooCommerce Subscriptions).
 * Version: 1.0.0
 * Author: MTDL
 */

if (!defined('ABSPATH')) {
    exit; // Segurança
}

// --- Reescrita para servir /version.json ---
function mtdl_pcm_feed_add_rewrite_rules() {
    add_rewrite_rule('^version\.json$', 'index.php?mtdl_pcm_version_json=1', 'top');
}
add_action('init', 'mtdl_pcm_feed_add_rewrite_rules');

function mtdl_pcm_feed_query_vars($vars) {
    $vars[] = 'mtdl_pcm_version_json';
    return $vars;
}
add_filter('query_vars', 'mtdl_pcm_feed_query_vars');

function mtdl_pcm_feed_template_redirect() {
    if (intval(get_query_var('mtdl_pcm_version_json')) === 1) {
        // Preflight CORS
        if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
            status_header(204);
            header('Access-Control-Allow-Origin: *');
            header('Access-Control-Allow-Methods: GET, OPTIONS');
            header('Access-Control-Allow-Headers: Content-Type');
            exit;
        }
        $version = get_option('mtdl_pcm_latest_version', '1.0.1');
        $download_url = get_option('mtdl_pcm_download_url', site_url('/downloads/pcm'));
        $changelog = get_option('mtdl_pcm_changelog', 'Correções de bugs e melhorias de desempenho');

        $payload = array(
            'latest_version' => $version,
            'download_url'   => $download_url,
            'changelog'      => $changelog,
        );

        status_header(200);
        header('Content-Type: application/json; charset=utf-8');
        header('Access-Control-Allow-Origin: *');
        header('X-Robots-Tag: noindex, nofollow');
        header('Cache-Control: no-cache, no-store, must-revalidate');
        header('Pragma: no-cache');
        header('Expires: 0');
        echo wp_json_encode($payload);
        exit;
    }
}
add_action('template_redirect', 'mtdl_pcm_feed_template_redirect');

register_activation_hook(__FILE__, function() {
    mtdl_pcm_feed_add_rewrite_rules();
    flush_rewrite_rules();
});
register_deactivation_hook(__FILE__, function() {
    flush_rewrite_rules();
});

// --- Rota REST alternativa: /wp-json/pcm/v1/version ---
add_action('rest_api_init', function () {
    register_rest_route('pcm/v1', '/version', array(
        'methods'  => 'GET',
        'callback' => function () {
            return array(
                'latest_version' => get_option('mtdl_pcm_latest_version', '1.0.1'),
                'download_url'   => get_option('mtdl_pcm_download_url', site_url('/downloads/pcm')),
                'changelog'      => get_option('mtdl_pcm_changelog', 'Correções de bugs e melhorias de desempenho'),
            );
        },
        'permission_callback' => '__return_true',
    ));
});

// --- Página de configurações ---
function mtdl_pcm_feed_admin_menu() {
    add_options_page('MTDL PCM', 'MTDL PCM', 'manage_options', 'mtdl-pcm-feed', 'mtdl_pcm_feed_settings_page');
}
add_action('admin_menu', 'mtdl_pcm_feed_admin_menu');

function mtdl_pcm_feed_register_settings() {
    register_setting('mtdl_pcm_feed', 'mtdl_pcm_latest_version');
    register_setting('mtdl_pcm_feed', 'mtdl_pcm_download_url');
    register_setting('mtdl_pcm_feed', 'mtdl_pcm_changelog');
}
add_action('admin_init', 'mtdl_pcm_feed_register_settings');

function mtdl_pcm_feed_settings_page() {
    if (!current_user_can('manage_options')) {
        return;
    }
    ?>
    <div class="wrap">
        <h1>MTDL PCM - Feed de Versão</h1>
        <p>Este plugin publica o feed em <code><?php echo esc_html(home_url('/version.json')); ?></code> e também em <code><?php echo esc_html(home_url('/wp-json/pcm/v1/version')); ?></code>.</p>
        <form method="post" action="options.php">
            <?php settings_fields('mtdl_pcm_feed'); ?>
            <table class="form-table" role="presentation">
                <tr>
                    <th scope="row"><label for="mtdl_pcm_latest_version">Versão mais recente</label></th>
                    <td><input type="text" id="mtdl_pcm_latest_version" name="mtdl_pcm_latest_version" value="<?php echo esc_attr(get_option('mtdl_pcm_latest_version', '1.0.1')); ?>" class="regular-text" /></td>
                </tr>
                <tr>
                    <th scope="row"><label for="mtdl_pcm_download_url">URL de download/página</label></th>
                    <td><input type="url" id="mtdl_pcm_download_url" name="mtdl_pcm_download_url" value="<?php echo esc_attr(get_option('mtdl_pcm_download_url', site_url('/downloads/pcm'))); ?>" class="regular-text" /></td>
                </tr>
                <tr>
                    <th scope="row"><label for="mtdl_pcm_changelog">Changelog</label></th>
                    <td><textarea id="mtdl_pcm_changelog" name="mtdl_pcm_changelog" class="regular-text" rows="4"><?php echo esc_textarea(get_option('mtdl_pcm_changelog', 'Correções de bugs e melhorias de desempenho')); ?></textarea></td>
                </tr>
            </table>
            <?php submit_button('Salvar alterações'); ?>
        </form>
    </div>
    <?php
}

// --- Shortcode do botão de download ---
function mtdl_pcm_feed_download_button_shortcode($atts = array()) {
    $atts = shortcode_atts(array(
        'label' => 'Baixar',
        'class' => 'button button-primary',
        'plans_url' => site_url('/planos'),
    ), $atts, 'pcm_download_button');

    $url = get_option('mtdl_pcm_download_url', site_url('/downloads/pcm'));

    // Se WooCommerce Subscriptions estiver presente, verifica assinatura ativa
    if (function_exists('wcs_user_has_subscription')) {
        $user_id = get_current_user_id();
        $has_active = ($user_id) ? wcs_user_has_subscription($user_id, '', 'active') : false;
        if (!$has_active) {
            return '<a class="' . esc_attr($atts['class']) . '" href="' . esc_url($atts['plans_url']) . '">Assinar para baixar</a>';
        }
    }

    return '<a class="' . esc_attr($atts['class']) . '" href="' . esc_url($url) . '">' . esc_html($atts['label']) . '</a>';
}
add_shortcode('pcm_download_button', 'mtdl_pcm_feed_download_button_shortcode');